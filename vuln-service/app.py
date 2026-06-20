import os
import sqlite3
import time
import subprocess
import hashlib
import jwt
from flask import Flask, request, jsonify, render_template, redirect, url_for, g

app = Flask(__name__)

# Configurable paths
DB_PATH = 'data.db'
FLAG_TXT_PATH = os.environ.get('FLAG_TXT_PATH', '/flag.txt')
FLAG_UPDATE_SECRET = os.environ.get('FLAG_UPDATE_SECRET', 'DefaultFlagUpdateSecretKey!')
TEAM_NAME = os.environ.get('TEAM_NAME', 'LocalTeam')

# Global environmental variable configuration key
os.environ['FLAG_ENV'] = os.environ.get('FLAG_ENV', 'FLAG{cyber_black_market_placeholder_env_flag}')

# Weak JWT secret loaded from config backup (which can be read from static/config.py.bak)
JWT_SECRET_KEY = "VulnServiceDefaultWeakSecretKey"

# -------------------------------------------------------------
# Database Setup and Initialization
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
        
        # User accounts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                balance REAL DEFAULT 100.0,
                role TEXT DEFAULT 'user'
            )
        ''')
        
        # Secret private messages containing FLAG 1
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS private_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT,
                receiver TEXT,
                message TEXT,
                is_secure INTEGER DEFAULT 1
            )
        ''')

        # Black Market items
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                price REAL,
                seller TEXT
            )
        ''')

        # Insert some items if empty
        cursor.execute("SELECT COUNT(*) FROM items")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO items (name, description, price, seller) VALUES ('Zero-day Exploit exploit RCE', 'Premium bypass for modern routers', 80.0, 'admin')")
            cursor.execute("INSERT INTO items (name, description, price, seller) VALUES ('Leaked Database Dump', '5 million accounts from local bank', 50.0, 'anonymous_hacker')")
            cursor.execute("INSERT INTO items (name, description, price, seller) VALUES ('Ransomware builder tool', 'Fully customizable payload generator', 120.0, 'malware_coder')")
        
        # Insert admin user and flag holding user if not exists
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO users (username, password, balance, role) VALUES ('admin', 'SuperSecuredAdminPassword2026!Password', 9999.0, 'admin')")
            cursor.execute("INSERT INTO users (username, password, balance, role) VALUES ('alice', 'alicepassword123', 100.0, 'user')")
            cursor.execute("INSERT INTO users (username, password, balance, role) VALUES ('bob', 'bobpassword456', 150.0, 'user')")
            cursor.execute("INSERT INTO users (username, password, balance, role) VALUES ('flag_holder', 'flagholderpass2026', 1000.0, 'user')")
            
            # Initial placeholder flag
            cursor.execute("INSERT INTO private_messages (sender, receiver, message, is_secure) VALUES ('admin', 'flag_holder', 'FLAG{cyber_black_market_dummy_db_flag}', 1)")
            
        db.commit()

# Initialize DB on import
if not os.path.exists(DB_PATH):
    init_db()
else:
    # Just ensure tables are there
    init_db()

# -------------------------------------------------------------
# Admin Flag Update API Endpoint (Called by Gameserver each round)
# -------------------------------------------------------------
@app.route('/admin/update_flags', methods=['POST'])
def update_flags():
    # Authentication check
    auth_header = request.headers.get('X-Flag-Update-Auth', '')
    if auth_header != FLAG_UPDATE_SECRET:
        return jsonify({"status": "error", "message": "Unauthorized Flag Update Request"}), 403
    
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Missing JSON payload"}), 400
        
    db_flag = data.get('db_flag')
    file_flag = data.get('file_flag')
    env_flag = data.get('env_flag')

    try:
        db = get_db()
        cursor = db.cursor()
        
        # Update flag 1 in private_messages
        if db_flag:
            cursor.execute("UPDATE private_messages SET message = ? WHERE receiver = 'flag_holder'", (db_flag,))
            db.commit()
            
        # Update flag 2 in flag.txt
        if file_flag:
            with open(FLAG_TXT_PATH, 'w') as f:
                f.write(file_flag + "\n")
                
        # Update flag 3 in environment/env_flag endpoint
        if env_flag:
            os.environ['FLAG_ENV'] = env_flag
            
        return jsonify({"status": "success", "message": "Flags updated successfully"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Endpoint to display environmental variable flag
@app.route('/env_flag', methods=['GET'])
def get_env_flag():
    # Safe check: limit to request headers or public but hidden
    return jsonify({"env_flag": os.environ.get('FLAG_ENV')})

# -------------------------------------------------------------
# Authentication helper
# -------------------------------------------------------------
def get_current_user():
    token = request.cookies.get('session_token')
    if not token:
        return None
    try:
        # Weak Crypto Vulnerability 6: We use PyJWT with a weak, hardcoded secret.
        # Vulnerable bypass: Attackers can extract secret from static/config.py.bak, sign a custom role: admin token
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
        return payload
    except Exception:
        return None

# -------------------------------------------------------------
# Web & API Frontend / Functionality
# -------------------------------------------------------------
@app.route('/')
def index():
    user = get_current_user()
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM items")
    items = cursor.fetchall()
    return render_template('index.html', user=user, items=items, team_name=TEAM_NAME)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        db = get_db()
        cursor = db.cursor()
        # Direct password verification for simplicity
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        
        if user:
            # Create session token with role
            token = jwt.encode({'username': user['username'], 'role': user['role']}, JWT_SECRET_KEY, algorithm='HS256')
            resp = redirect(url_for('index'))
            resp.set_cookie('session_token', token)
            return resp
        else:
            return render_template('login.html', error="Invalid credentials", team_name=TEAM_NAME)
    return render_template('login.html', team_name=TEAM_NAME)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            return render_template('register.html', error="Missing username or password", team_name=TEAM_NAME)
            
        db = get_db()
        cursor = db.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            db.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return render_template('register.html', error="Username already exists", team_name=TEAM_NAME)
    return render_template('register.html', team_name=TEAM_NAME)

@app.route('/logout')
def logout():
    resp = redirect(url_for('index'))
    resp.set_cookie('session_token', '', expires=0)
    return resp

# -------------------------------------------------------------
# Vulnerability 1: Race Condition (Withdraw / Money Transfer)
# -------------------------------------------------------------
@app.route('/api/withdraw', methods=['POST'])
def withdraw():
    user = get_current_user()
    if not user:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
    amount_str = request.form.get('amount')
    if not amount_str:
         return jsonify({"status": "error", "message": "Missing amount"}), 400
         
    try:
        amount = float(amount_str)
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid amount format"}), 400

    if amount <= 0:
        return jsonify({"status": "error", "message": "Amount must be positive"}), 400

    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    cursor = db.cursor()
    
    # 1. Fetch current balance
    cursor.execute("SELECT balance FROM users WHERE username = ?", (user['username'],))
    row = cursor.fetchone()
    if not row:
        db.close()
        return jsonify({"status": "error", "message": "User not found"}), 404
        
    current_balance = row['balance']
    
    # Check if balance is sufficient
    if current_balance < amount:
        db.close()
        return jsonify({"status": "error", "message": "Insufficient balance"}), 400
        
    # 2. Race Condition Trigger: Sleep 0.5s before setting new balance
    # Vulnerable logic: Multiple requests can query balance before any writes happen.
    time.sleep(0.5)
    
    new_balance = current_balance - amount
    
    # 3. Update database balance
    cursor.execute("UPDATE users SET balance = ? WHERE username = ?", (new_balance, user['username']))
    db.commit()
    db.close()
    
    return jsonify({"status": "success", "new_balance": new_balance, "message": f"Successfully withdrew ${amount}"})

# Money transfer interface page
@app.route('/wallet', methods=['GET', 'POST'])
def wallet():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
        
    db = get_db()
    cursor = db.cursor()
    
    if request.method == 'POST':
        # Handles standard transfers (not using the API endpoint, but standard forms)
        # We will keep the wallet transfer standard but redirect race-condition attackers to the API.
        pass
        
    cursor.execute("SELECT balance FROM users WHERE username = ?", (user['username'],))
    row = cursor.fetchone()
    balance = row['balance'] if row else 0.0
    return render_template('wallet.html', user=user, balance=balance, team_name=TEAM_NAME)

# -------------------------------------------------------------
# Vulnerability 2: IDOR (Insecure Direct Object Reference)
# -------------------------------------------------------------
# This API endpoint allows anyone to fetch details of a private message by index ID without verification.
@app.route('/api/message/<int:msg_id>', methods=['GET'])
def get_message(msg_id):
    user = get_current_user()
    if not user:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
    db = get_db()
    cursor = db.cursor()
    
    # Vulnerable IDOR code: Does not verify if 'receiver' or 'sender' matches current user
    # Vulnerability: Anyone can query ID 1 to get the Flag user's private message
    cursor.execute("SELECT * FROM private_messages WHERE id = ?", (msg_id,))
    msg = cursor.fetchone()
    
    if not msg:
        return jsonify({"status": "error", "message": "Message not found"}), 404
        
    return jsonify({
        "id": msg['id'],
        "sender": msg['sender'],
        "receiver": msg['receiver'],
        "message": msg['message'],
        "is_secure": msg['is_secure']
    })

# Messages user interface page
@app.route('/messages')
def messages():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
        
    db = get_db()
    cursor = db.cursor()
    # Safe rendering for visual web users (queries user's own messages)
    cursor.execute("SELECT * FROM private_messages WHERE sender = ? OR receiver = ?", (user['username'], user['username']))
    msgs = cursor.fetchall()
    return render_template('messages.html', user=user, messages=msgs, team_name=TEAM_NAME)

# Send message action
@app.route('/api/message/send', methods=['POST'])
def send_message():
    user = get_current_user()
    if not user:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
    receiver = request.form.get('receiver')
    message = request.form.get('message')
    
    if not receiver or not message:
        return jsonify({"status": "error", "message": "Missing receiver or message"}), 400
        
    db = get_db()
    cursor = db.cursor()
    cursor.execute("INSERT INTO private_messages (sender, receiver, message) VALUES (?, ?, ?)", (user['username'], receiver, message))
    db.commit()
    return jsonify({"status": "success", "message": "Message sent!"})

# -------------------------------------------------------------
# Vulnerability 3: SQL Injection (SQLi)
# -------------------------------------------------------------
@app.route('/search', methods=['GET'])
def search_items():
    user = get_current_user()
    query = request.args.get('q', '')
    
    db = get_db()
    cursor = db.cursor()
    
    results = []
    error = None
    if query:
        # Vulnerable SQLi Code: String concatenation directly in the execution query
        # Mitigated Code would be: cursor.execute("SELECT * FROM items WHERE name LIKE ?", (f'%{query}%',))
        sql_query = f"SELECT * FROM items WHERE name LIKE '%{query}%' OR description LIKE '%{query}%'"
        try:
            cursor.execute(sql_query)
            results = cursor.fetchall()
        except sqlite3.Error as e:
            error = str(e)
            
    return render_template('search.html', user=user, results=results, query=query, error=error, team_name=TEAM_NAME)

# -------------------------------------------------------------
# Vulnerability 4: Command Injection / RCE
# -------------------------------------------------------------
@app.route('/api/network_check', methods=['POST'])
def network_check():
    user = get_current_user()
    if not user:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
    target = request.form.get('target', '')
    if not target:
        return jsonify({"status": "error", "message": "Missing partner target"}), 400
        
    # Vulnerable RCE: Runs shell command via system/subprocess with shell=True
    # Vulnerability: target="8.8.8.8; cat /flag.txt" will execute both commands.
    command = f"ping -c 2 -W 2 {target}"
    
    try:
        output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, text=True)
        return jsonify({"status": "success", "output": output})
    except subprocess.CalledProcessError as e:
        return jsonify({"status": "error", "output": e.output})

# System diagnostic interface page
@app.route('/diagnostics')
def diagnostics():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    return render_template('diagnostics.html', user=user, team_name=TEAM_NAME)

# -------------------------------------------------------------
# Vulnerability 5: Broken Object Level Authorization (BOLA)
# -------------------------------------------------------------
@app.route('/api/profile/update', methods=['POST'])
def update_profile():
    # Vulnerability: Does not authenticate token correctly or lacks validation,
    # allows upgrading role field from payload
    user = get_current_user()
    if not user:
         return jsonify({"status": "error", "message": "Unauthorized"}), 401
         
    data = request.get_json()
    if not data:
         return jsonify({"status": "error", "message": "Missing update payload"}), 400
         
    # Exposing dynamic updates on user fields including 'role' or 'balance' directly.
    username_to_update = data.get('username', user['username'])
    new_role = data.get('role')
    new_balance = data.get('balance')
    
    # BOLA flaw: We trust username from parameters/JSON instead of session token,
    # and fail to restrict parameter changes like 'role'
    db = get_db()
    cursor = db.cursor()
    
    try:
        if new_role:
            cursor.execute("UPDATE users SET role = ? WHERE username = ?", (new_role, username_to_update))
        if new_balance is not None:
            cursor.execute("UPDATE users SET balance = ? WHERE username = ?", (new_balance, username_to_update))
            
        db.commit()
        
        # If updating oneself, regenerate token
        if username_to_update == user['username']:
            # Fetch updated values
            cursor.execute("SELECT * FROM users WHERE username = ?", (user['username'],))
            updated_user = cursor.fetchone()
            token = jwt.encode({'username': updated_user['username'], 'role': updated_user['role']}, JWT_SECRET_KEY, algorithm='HS256')
            resp = jsonify({"status": "success", "message": "Profile updated successfully"})
            resp.set_cookie('session_token', token)
            return resp
            
        return jsonify({"status": "success", "message": f"Updated profile for {username_to_update}"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Profile management interface page
@app.route('/profile')
def profile():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
        
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (user['username'],))
    db_user = cursor.fetchone()
    return render_template('profile.html', user=user, db_user=db_user, team_name=TEAM_NAME)

# -------------------------------------------------------------
# Vulnerability 6: Weak Cryptography (Coupon Center)
# -------------------------------------------------------------
# Custom algorithm: md5(username + SALT) where SALT is "WEAK_SALT"
SALT = "WEAK_SALT"

@app.route('/api/coupon/claim', methods=['POST'])
def claim_coupon():
    user = get_current_user()
    if not user:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
    coupon_code = request.form.get('coupon_code', '')
    if not coupon_code:
        return jsonify({"status": "error", "message": "Missing coupon code"}), 400
        
    # Weak Crypto verify: The code must equal md5(username + "WEAK_SALT")
    expected_hash = hashlib.md5((user['username'] + SALT).encode()).hexdigest()
    
    if coupon_code == expected_hash:
        # Credit user $500 balance
        db = get_db()
        cursor = db.cursor()
        cursor.execute("UPDATE users SET balance = balance + 500.0 WHERE username = ?", (user['username'],))
        db.commit()
        return jsonify({"status": "success", "message": "Coupon code verified! Credited $500 to account."})
    else:
        return jsonify({"status": "error", "message": "Invalid transaction token / coupon code."})

# Coupon page
@app.route('/coupons')
def coupons():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    return render_template('coupons.html', user=user, team_name=TEAM_NAME)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
