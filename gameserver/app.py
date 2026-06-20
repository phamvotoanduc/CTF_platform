import os
import sqlite3
import random
import string
import time
import threading
import requests
from flask import Flask, request, jsonify, render_template, redirect, url_for, g, session
from sla_checker import run_sla_check

app = Flask(__name__)
app.secret_key = os.environ.get('SESSION_SECRET', 'GameserverCyberBlackMarketKey2026')

DB_PATH = 'data/gameserver.db'

# Admin parameters
ADMIN_SECRET = os.environ.get('ADMIN_SECRET', 'SuperSecretAdminKey1337!')
ROUND_DURATION = 120 # seconds (2 minutes)

# Preconfigured Teams in the environment
# Hostnames in Docker networks: team1-service, team2-service
TEAMS_CONFIG = [
    {"id": 1, "name": "Team 1", "host": "team1-service", "port": 5000, "flag_secret": "Team1FlagUpdateSecretKey2026!"},
    {"id": 2, "name": "Team 2", "host": "team2-service", "port": 5000, "flag_secret": "Team2FlagUpdateSecretKey2026!"}
]

# -------------------------------------------------------------
# Database Setup
# -------------------------------------------------------------
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        
        # User accounts for Teams
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                display_name TEXT NOT NULL,
                attack_points REAL DEFAULT 0.0,
                defense_points REAL DEFAULT 0.0,
                sla_points REAL DEFAULT 0.0
            )
        ''')
        
        # Game state parameters
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS game_state (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')

        # Flag logs generated for tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS flag_logs (
                round INTEGER,
                team_id INTEGER,
                flag_type TEXT, -- 'db', 'file', 'env'
                flag_value TEXT,
                is_captured INTEGER DEFAULT 0
            )
        ''')

        # SLA checks histories
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sla_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                round INTEGER,
                team_id INTEGER,
                status TEXT, -- 'UP', 'DOWN'
                reason TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Submitted flags history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                submitting_team_id INTEGER,
                target_team_id INTEGER,
                flag_value TEXT,
                points REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Set initial game variables
        cursor.execute("INSERT OR IGNORE INTO game_state (key, value) VALUES ('current_round', '0')")
        cursor.execute("INSERT OR IGNORE INTO game_state (key, value) VALUES ('game_started', '0')")
        cursor.execute("INSERT OR IGNORE INTO game_state (key, value) VALUES ('round_end_time', '0')")
        
        # Insert pre-configured teams if empty
        cursor.execute("SELECT COUNT(*) FROM teams")
        if cursor.fetchone()[0] == 0:
            for t in TEAMS_CONFIG:
                cursor.execute(
                    "INSERT INTO teams (id, username, password, display_name, attack_points, defense_points, sla_points) VALUES (?, ?, ?, ?, 0, 0, 0)",
                    (t['id'], f"team{t['id']}", f"teampassword{t['id']}", t['name'])
                )
        db.commit()

# Ensure directories and databases exist
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
init_db()

# -------------------------------------------------------------
# Core Attack-Defense Game Loop Engine
# -------------------------------------------------------------
def generate_flag():
    random_hash = ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))
    return f"FLAG{{cyber_black_market_{random_hash}}}"

def run_round_tick():
    """
    Called at the start of a round to:
    1. Increment round ID
    2. Generate and upload flags to all vuln-service instances
    3. Run SLA checker on all vuln-service instances and compute points
    """
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    cursor = db.cursor()
    
    # Get game start state
    cursor.execute("SELECT value FROM game_state WHERE key = 'game_started'")
    if cursor.fetchone()['value'] != '1':
        db.close()
        return

    # Increment round
    cursor.execute("SELECT value FROM game_state WHERE key = 'current_round'")
    curr_round = int(cursor.fetchone()['value']) + 1
    cursor.execute("UPDATE game_state SET value = ? WHERE key = 'current_round'", (str(curr_round),))
    
    # Calculate round end time
    round_end_time = int(time.time()) + ROUND_DURATION
    cursor.execute("UPDATE game_state SET value = ? WHERE key = 'round_end_time'", (str(round_end_time),))
    db.commit()

    print(f"[ROUND ENGINE] Starting Round {curr_round}. End time: {round_end_time}")

    # Generate flags and upload for each team
    for team in TEAMS_CONFIG:
        db_flag = generate_flag()
        file_flag = generate_flag()
        env_flag = generate_flag()

        # Log generated flags
        cursor.execute("INSERT INTO flag_logs (round, team_id, flag_type, flag_value) VALUES (?, ?, 'db', ?)", (curr_round, team['id'], db_flag))
        cursor.execute("INSERT INTO flag_logs (round, team_id, flag_type, flag_value) VALUES (?, ?, 'file', ?)", (curr_round, team['id'], file_flag))
        cursor.execute("INSERT INTO flag_logs (round, team_id, flag_type, flag_value) VALUES (?, ?, 'env', ?)", (curr_round, team['id'], env_flag))
        db.commit()

        # Upload flags to vuln-service instance
        upload_url = f"http://{team['host']}:{team['port']}/admin/update_flags"
        headers = {'X-Flag-Update-Auth': team['flag_secret']}
        payload = {
            "db_flag": db_flag,
            "file_flag": file_flag,
            "env_flag": env_flag
        }
        try:
            r = requests.post(upload_url, json=payload, headers=headers, timeout=5)
            print(f"[ROUND ENGINE] Uploaded flags to {team['name']}: {r.status_code}")
        except Exception as e:
            print(f"[ROUND ENGINE] Failed to upload flags to {team['name']}: {e}")

    # SLA Checking Stage
    for team in TEAMS_CONFIG:
        # Determine internal host/port to check
        is_up, reason = run_sla_check(team['host'], team['port'])
        status = 'UP' if is_up else 'DOWN'
        
        cursor.execute(
            "INSERT INTO sla_logs (round, team_id, status, reason) VALUES (?, ?, ?, ?)",
            (curr_round, team['id'], status, reason)
        )
        
        if is_up:
            # Grant SLA uptime points (+10 per round)
            cursor.execute("UPDATE teams SET sla_points = sla_points + 10.0 WHERE id = ?", (team['id'],))
        else:
            # Deduct SLA points for downtime (-5 per round)
            cursor.execute("UPDATE teams SET sla_points = sla_points - 5.0 WHERE id = ?", (team['id'],))
        db.commit()

    db.close()

def game_loop_thread():
    """Background loop that sleeps and runs round engine ticks."""
    while True:
        try:
            db = sqlite3.connect(DB_PATH)
            db.row_factory = sqlite3.Row
            cursor = db.cursor()
            cursor.execute("SELECT value FROM game_state WHERE key = 'game_started'")
            game_started = cursor.fetchone()['value'] == '1'
            
            if game_started:
                cursor.execute("SELECT value FROM game_state WHERE key = 'round_end_time'")
                round_end_time = int(cursor.fetchone()['value'])
                now = int(time.time())
                
                if now >= round_end_time:
                    # Time to trigger new round!
                    run_round_tick()
            db.close()
        except Exception as e:
            print(f"[GAME LOOP THREAD ERROR] {e}")
        time.sleep(2)

# Start background manager thread
bg_thread = threading.Thread(target=game_loop_thread, daemon=True)
bg_thread.start()

# -------------------------------------------------------------
# Gameserver Web Routes
# -------------------------------------------------------------
def get_game_state_dict():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM game_state")
    rows = cursor.fetchall()
    return {r['key']: r['value'] for r in rows}

@app.route('/')
def index():
    state = get_game_state_dict()
    db = get_db()
    cursor = db.cursor()
    
    # Fetch team metrics
    cursor.execute("SELECT *, (attack_points + defense_points + sla_points) as total_points FROM teams ORDER BY total_points DESC")
    leaderboard = cursor.fetchall()
    
    # Calculate time remaining in round
    round_end = int(state.get('round_end_time', 0))
    time_left = max(0, round_end - int(time.time()))
    
    return render_template('index.html', state=state, leaderboard=leaderboard, time_left=time_left)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM teams WHERE username = ? AND password = ?", (username, password))
        team = cursor.fetchone()
        
        if team:
            session['team_id'] = team['id']
            session['display_name'] = team['display_name']
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="Invalid team login credentials")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# Submit Flag Portal
@app.route('/submit', methods=['GET', 'POST'])
def submit_flag():
    if 'team_id' not in session:
        return redirect(url_for('login'))
        
    team_id = session['team_id']
    status_msg = None
    status_type = "info"
    
    if request.method == 'POST':
        flag_submitted = request.form.get('flag', '').strip()
        
        db = get_db()
        cursor = db.cursor()
        
        # Check current round
        cursor.execute("SELECT value FROM game_state WHERE key = 'current_round'")
        curr_round = int(cursor.fetchone()['value'])
        
        # Look for the flag in flag logs
        # To avoid replay attacks, check if flag is valid in current round or past 1 round
        cursor.execute(
            "SELECT * FROM flag_logs WHERE flag_value = ? AND round IN (?, ?)", 
            (flag_submitted, curr_round, curr_round - 1)
        )
        flag_record = cursor.fetchone()
        
        if not flag_record:
            status_msg = "Error: Invalid or expired flag code!"
            status_type = "danger"
        elif flag_record['team_id'] == team_id:
            status_msg = "Warning: You cannot submit your own flag!"
            status_type = "warning"
        else:
            # Check if this team has already submitted this specific flag
            cursor.execute(
                "SELECT COUNT(*) FROM submissions WHERE submitting_team_id = ? AND flag_value = ?",
                (team_id, flag_submitted)
            )
            already_submitted = cursor.fetchone()[0] > 0
            
            if already_submitted:
                status_msg = "Warning: You have already scored points for this flag!"
                status_type = "warning"
            else:
                # Insert submission log
                points_granted = 20.0
                cursor.execute(
                    "INSERT INTO submissions (submitting_team_id, target_team_id, flag_value, points) VALUES (?, ?, ?, ?)",
                    (team_id, flag_record['team_id'], flag_submitted, points_granted)
                )
                
                # Update attacker score
                cursor.execute("UPDATE teams SET attack_points = attack_points + ? WHERE id = ?", (points_granted, team_id))
                
                # Deduct defense points of target team (Defense loss)
                cursor.execute("UPDATE teams SET defense_points = defense_points - 10.0 WHERE id = ?", (flag_record['team_id'],))
                
                # Mark flag log as captured
                cursor.execute("UPDATE flag_logs SET is_captured = 1 WHERE flag_value = ?", (flag_submitted,))
                
                db.commit()
                status_msg = f"Success! Correct flag submitted. Gained +{points_granted} attack points."
                status_type = "success"
                
    return render_template('submit.html', status_msg=status_msg, status_type=status_type)

# Service Status Uptime Monitor
@app.route('/monitor')
def monitor():
    db = get_db()
    cursor = db.cursor()
    
    # Fetch current round
    cursor.execute("SELECT value FROM game_state WHERE key = 'current_round'")
    curr_round = int(cursor.fetchone()['value'])
    
    # Fetch team service status from last round
    cursor.execute("""
        SELECT teams.display_name, sla_logs.status, sla_logs.reason, sla_logs.timestamp
        FROM teams
        LEFT JOIN sla_logs ON teams.id = sla_logs.team_id AND sla_logs.round = ?
    """, (curr_round,))
    logs = cursor.fetchall()
    
    return render_template('monitor.html', logs=logs, round_num=curr_round)

# API endpoint for leaderboard AJAX polling
@app.route('/api/leaderboard')
def api_leaderboard():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, display_name, attack_points, defense_points, sla_points, (attack_points + defense_points + sla_points) as total_points FROM teams ORDER BY total_points DESC")
    teams = [dict(row) for row in cursor.fetchall()]
    
    state = get_game_state_dict()
    round_end = int(state.get('round_end_time', 0))
    time_left = max(0, round_end - int(time.time()))
    
    return jsonify({
        "teams": teams,
        "current_round": state.get('current_round', '0'),
        "game_started": state.get('game_started', '0'),
        "time_left": time_left
    })

# -------------------------------------------------------------
# Admin Control Panel
# -------------------------------------------------------------
@app.route('/admin', methods=['GET', 'POST'])
def admin_panel():
    secret = request.args.get('secret')
    if secret != ADMIN_SECRET:
         return "Forbidden: Missing or invalid secret key.", 403
         
    db = get_db()
    cursor = db.cursor()
    
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'start':
            cursor.execute("UPDATE game_state SET value = '1' WHERE key = 'game_started'")
            db.commit()
            # Trigger first round tick immediately
            run_round_tick()
        elif action == 'stop':
            cursor.execute("UPDATE game_state SET value = '0' WHERE key = 'game_started'")
            db.commit()
        elif action == 'force_tick':
            run_round_tick()
            
        return redirect(url_for('admin_panel', secret=ADMIN_SECRET))
        
    state = get_game_state_dict()
    return render_template('admin.html', state=state, secret=ADMIN_SECRET)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
