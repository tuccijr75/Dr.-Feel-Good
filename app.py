
import os
import json
import base64
from datetime import datetime
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# -----------------------------
# GitHub Config
# -----------------------------
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # set in Render
GITHUB_REPO = os.getenv("GITHUB_REPO", "tuccijr75/Dr.-Feel-Good")  # e.g. "michaelrobertucci/mood-tracker"
BRANCH = os.getenv("GITHUB_BRANCH", "main")

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

# -----------------------------
# Helper: Write JSON to Repo
# -----------------------------
def write_json_to_repo(file_path, new_entry):
    """Appends or creates a JSON file in the GitHub repo"""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{file_path}"

    # Check if file exists
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        data = response.json()
        sha = data["sha"]
        content = base64.b64decode(data["content"]).decode("utf-8")
        try:
            json_data = json.loads(content)
        except json.JSONDecodeError:
            json_data = []
    else:
        sha = None
        json_data = []

    # Append new entry
    json_data.append(new_entry)

    # Encode and push to GitHub
    encoded_content = base64.b64encode(
        json.dumps(json_data, indent=2).encode("utf-8")
    ).decode("utf-8")

    payload = {
        "message": f"Update {file_path}",
        "content": encoded_content,
        "branch": BRANCH
    }
    if sha:
        payload["sha"] = sha

    put_response = requests.put(url, headers=HEADERS, json=payload)
    if put_response.status_code not in [200, 201]:
        raise Exception(f"GitHub update failed: {put_response.text}")

    return put_response.json()

# -----------------------------
# Endpoints
# -----------------------------

@app.route("/")
def home():
    return jsonify({"status": "ok", "message": "Mood/Reminder logger running"})

@app.route("/log-mood", methods=["POST"])
def log_mood():
    """POST a mood log: {mood, notes}"""
    data = request.json
    entry = {
        "date": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "mood": data.get("mood", "neutral"),
        "notes": data.get("notes", "")
    }
    write_json_to_repo("logs/mood_log.json", entry)
    return jsonify({"status": "success", "entry": entry})

@app.route("/add-reminder", methods=["POST"])
def add_reminder():
    """POST a reminder: {reminder, due_date}"""
    data = request.json
    entry = {
        "id": int(datetime.utcnow().timestamp()),  # unique-ish id
        "reminder": data.get("reminder"),
        "due_date": data.get("due_date"),
        "status": "pending"
    }
    write_json_to_repo("logs/reminders.json", entry)
    return jsonify({"status": "success", "entry": entry})

@app.route("/get-reminders", methods=["GET"])
def get_reminders():
    """Fetch reminders.json from GitHub"""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/logs/reminders.json"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        data = response.json()
        content = base64.b64decode(data["content"]).decode("utf-8")
        return jsonify(json.loads(content))
    else:
        return jsonify([])

@app.route("/get-moods", methods=["GET"])
def get_moods():
    """Fetch mood_log.json from GitHub"""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/logs/mood_log.json"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        data = response.json()
        content = base64.b64decode(data["content"]).decode("utf-8")
        return jsonify(json.loads(content))
    else:
        return jsonify([])

# -----------------------------
# Run locally
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
