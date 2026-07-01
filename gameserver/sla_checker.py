import requests

def run_sla_check(target_host, target_port):
    """
    Performs transactions on a target vuln-service instance to verify SLA status.
    Returns (is_up, reason)
    """
    base_url = f"http://{target_host}:{target_port}"
    session = requests.Session()
    
    # Generate unique test user
    import time
    test_user = f"sla_user_{int(time.time())}"
    test_pass = "sla_password_123"

    try:
        # Check 1: Home page loading
        r = session.get(base_url, timeout=3)
        if r.status_code != 200:
            return False, "Home page returned status " + str(r.status_code)

        # Check 2: Register user
        r = session.post(f"{base_url}/register", data={
            "username": test_user,
            "password": test_pass
        }, timeout=3)
        if r.status_code != 200 and "already exists" not in r.text:
            return False, "Registration endpoint failed"

        # Check 3: Login user
        r = session.post(f"{base_url}/login", data={
            "username": test_user,
            "password": test_pass
        }, timeout=3)
        if r.status_code != 200 or "Logged in as" not in r.text:
            return False, "Login validation failed"

        # Check 4: Send a secure message
        r = session.post(f"{base_url}/api/message/send", data={
            "receiver": "admin",
            "message": "SLA test message payload"
        }, timeout=3)
        if r.status_code != 200:
            return False, "Failed to send private message"

        # Check 5: Run search query
        r = session.get(f"{base_url}/search?q=Exploit", timeout=3)
        if r.status_code != 200 or "RCE" not in r.text:
            # RCE is in listing items
            return False, "Search catalog lookup query failed"

        # Check 6: Update profile (BOLA validation check)
        r = session.post(f"{base_url}/api/profile/update", json={
            "username": test_user,
            "role": "moderator"
        }, timeout=3)
        if r.status_code != 200:
             return False, "Profile update API (BOLA) failed"

        return True, "All services checks passed"

    except requests.exceptions.RequestException as e:
        return False, f"Connection timeout/refused: {str(e)}"
