import os
import subprocess
import threading
from flask import Flask, request, jsonify

app = Flask(__name__)

# Webhook authentication secret configured in Gitea
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "GiteaWebhookSecretKey2026")
WORKSPACE_DIR = "/workspace" # Mount directory of the workspace on host

def execute_deploy(team_name, repo_name):
    """Runs git pull and docker-compose build/up in a background thread."""
    try:
        repo_path = os.path.join(WORKSPACE_DIR, "teams", repo_name)
        print(f"[DEPLOY] Starting redeployment for {team_name} in {repo_path}")
        
        # 1. Git pull
        # Disable git host key checking for local HTTP git
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"
        
        pull_cmd = ["git", "pull", "origin", "main"]
        pull_res = subprocess.run(pull_cmd, cwd=repo_path, capture_output=True, text=True, env=env)
        print(f"[DEPLOY] git pull stdout:\n{pull_res.stdout}\nstderr:\n{pull_res.stderr}")
        
        if pull_res.returncode != 0:
            print(f"[DEPLOY ERROR] Git pull failed with code {pull_res.returncode}")
            return
            
        # 2. Docker compose rebuild and restart target service
        # Service name in docker-compose: team1-service or team2-service
        service_name = f"{team_name}-service"
        
        compose_file = os.path.join(WORKSPACE_DIR, "docker-compose.yml")
        
        build_cmd = ["docker", "compose", "-f", compose_file, "build", service_name]
        build_res = subprocess.run(build_cmd, capture_output=True, text=True)
        print(f"[DEPLOY] docker compose build stdout:\n{build_res.stdout}\nstderr:\n{build_res.stderr}")
        
        up_cmd = ["docker", "compose", "-f", compose_file, "up", "-d", service_name]
        up_res = subprocess.run(up_cmd, capture_output=True, text=True)
        print(f"[DEPLOY] docker compose up stdout:\n{up_res.stdout}\nstderr:\n{up_res.stderr}")
        
        print(f"[DEPLOY SUCCESS] Redeployment finished for {team_name}")
        
    except Exception as e:
        print(f"[DEPLOY FATAL ERROR] Exception during deploy: {str(e)}")

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    # Verify request signature/token
    secret = request.headers.get("X-Gitea-Signature") or request.json.get("secret")
    if secret != WEBHOOK_SECRET:
         return jsonify({"status": "error", "message": "Invalid webhook secret signature"}), 403
         
    data = request.json
    if not data:
         return jsonify({"status": "error", "message": "Missing payload"}), 400
         
    repo_name = data.get("repository", {}).get("name", "")
    ref = data.get("ref", "")
    
    # We only auto-deploy pushes to main branch
    if ref != "refs/heads/main":
        return jsonify({"status": "ignored", "message": f"Push ref '{ref}' is not 'refs/heads/main'"}), 200
        
    if repo_name in ["team1-service", "team2-service"]:
        team_name = "team1" if repo_name == "team1-service" else "team2"
        
        # Run deploy script asynchronously so we return HTTP 200 immediately to Gitea
        thread = threading.Thread(target=execute_deploy, args=(team_name, repo_name))
        thread.start()
        
        return jsonify({"status": "queued", "message": f"Deployment queued for {team_name}"}), 200
    else:
        return jsonify({"status": "ignored", "message": f"Unknown repository '{repo_name}'"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9000)
