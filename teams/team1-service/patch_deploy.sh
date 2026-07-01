#!/bin/bash
# Helper script to automatically commit and push patches to Gitea without Git errors.

# 1. Configure local Git identity if not set
if [ -z "$(git config user.name)" ]; then
    git config user.name "Player"
    echo "[INFO] Set local git user.name to 'Player'"
fi
if [ -z "$(git config user.email)" ]; then
    git config user.email "player@example.com"
    echo "[INFO] Set local git user.email to 'player@example.com'"
fi

# 2. Stage changes
if [ -f "app.py" ]; then
    git add app.py
    echo "[*] Staged app.py"
else
    echo "[ERROR] app.py not found in the current directory."
    exit 1
fi

# 3. Commit changes
git commit -m "Patch: Update app.py" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "[*] Created new patch commit."
else
    echo "[INFO] No new changes to commit (working tree already clean)."
fi

# 4. Force push to Gitea to avoid non-fast-forward rejects
echo "[*] Pushing patch to Gitea..."
git push origin main --force
if [ $? -eq 0 ]; then
    echo -e "\n[SUCCESS] Patch deployed successfully! Gitea webhook triggered."
else
    echo -e "\n[FAILED] Failed to push to Gitea. Check your network or credentials."
fi
