import os
import shutil
import subprocess
import time
import requests

GITEA_URL = "http://localhost:3000"
GITEA_API = f"{GITEA_URL}/api/v1"
WEBHOOK_SECRET = "GiteaWebhookSecretKey2026"

def run_command(cmd, cwd=None):
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    if res.returncode != 0:
        print(f"[ERROR CMD] {cmd} failed:\n{res.stderr}")
    return res

def wait_for_gitea():
    print("[SETUP] Waiting for Gitea service to start up at localhost:3000...")
    for _ in range(30):
        try:
            r = requests.get(GITEA_URL, timeout=2)
            if r.status_code == 200:
                print("[SETUP] Gitea is online.")
                return True
        except requests.RequestException:
            pass
        time.sleep(2)
    print("[ERROR] Gitea failed to start in time.")
    return False

def setup_gitea():
    # 0. Clean up existing users to allow re-runs
    print("[SETUP] Cleaning up existing Gitea users...")
    run_command("docker exec --user git ctf-gitea gitea admin user delete --username gitea_admin")
    run_command("docker exec --user git ctf-gitea gitea admin user delete --username team1")
    run_command("docker exec --user git ctf-gitea gitea admin user delete --username team2")

    # 1. Create Admin Account inside Gitea container
    print("[SETUP] Creating Gitea admin user...")
    run_command("docker exec --user git ctf-gitea gitea admin user create --username gitea_admin --password AdminGiteaPassword2026! --email admin@example.com --admin --must-change-password=false")

    # 2. Create Team Users
    print("[SETUP] Creating team1 and team2 users...")
    run_command("docker exec --user git ctf-gitea gitea admin user create --username team1 --password teampassword1 --email team1@example.com --must-change-password=false")
    run_command("docker exec --user git ctf-gitea gitea admin user create --username team2 --password teampassword2 --email team2@example.com --must-change-password=false")

    # 3. Create Gitea Repositories via API
    # Team 1 repo
    print("[SETUP] Creating Gitea repository team1-service...")
    r1 = requests.post(f"{GITEA_API}/user/repos", json={"name": "team1-service", "private": False}, auth=('team1', 'teampassword1'))
    print(f"Response: {r1.status_code}")

    # Team 2 repo
    print("[SETUP] Creating Gitea repository team2-service...")
    r2 = requests.post(f"{GITEA_API}/user/repos", json={"name": "team2-service", "private": False}, auth=('team2', 'teampassword2'))
    print(f"Response: {r2.status_code}")

    # 4. Inject Initial Code Template
    print("[SETUP] Injecting template code to Gitea repositories...")
    temp_git = "vuln-service-git-temp"
    
    # Copy template files to a temporary folder
    if os.path.exists(temp_git):
        shutil.rmtree(temp_git)
    shutil.copytree("vuln-service", temp_git)
    
    # Initialize Git and push
    run_command("git init", cwd=temp_git)
    run_command("git config user.name 'CTF Organizer'", cwd=temp_git)
    run_command("git config user.email 'organizer@example.com'", cwd=temp_git)
    run_command("git checkout -b main", cwd=temp_git)
    run_command("git add .", cwd=temp_git)
    run_command("git commit -m 'Initial vulnerable service base template'", cwd=temp_git)
    
    # Push to Team 1
    run_command("git push -f http://team1:teampassword1@localhost:3000/team1/team1-service.git main", cwd=temp_git)
    
    # Push to Team 2
    run_command("git push -f http://team2:teampassword2@localhost:3000/team2/team2-service.git main", cwd=temp_git)
    
    # Clean up temp folder
    shutil.rmtree(temp_git)

    # 5. Set Up Webhooks for deployment notifications
    print("[SETUP] Creating webhook triggers in Gitea repositories...")
    webhook_payload = {
        "type": "gitea",
        "config": {
            "url": "http://deploy-webhook:9000/webhook",
            "content_type": "json",
            "secret": WEBHOOK_SECRET
        },
        "events": ["push"],
        "active": True
    }
    
    # Team 1 Webhook
    requests.post(f"{GITEA_API}/repos/team1/team1-service/hooks", json=webhook_payload, auth=('team1', 'teampassword1'))
    # Team 2 Webhook
    requests.post(f"{GITEA_API}/repos/team2/team2-service/hooks", json=webhook_payload, auth=('team2', 'teampassword2'))

    # 6. Clone local team working copies
    print("[SETUP] Cloning local working copies for docker compose builds...")
    teams_dir = "teams"
    if os.path.exists(teams_dir):
        shutil.rmtree(teams_dir)
    os.makedirs(teams_dir, exist_ok=True)
    
    run_command("git clone http://team1:teampassword1@localhost:3000/team1/team1-service.git team1-service", cwd=teams_dir)
    run_command("git clone http://team2:teampassword2@localhost:3000/team2/team2-service.git team2-service", cwd=teams_dir)
    
    print("[SETUP COMPLETE] Gitea and Git CI/CD system successfully automated and configured!")

if __name__ == "__main__":
    if wait_for_gitea():
        setup_gitea()
