import os
import json
import base64
from datetime import datetime, timezone
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# -------------------------------------------------
# Config: GitHub repo + token via Render env vars
# -------------------------------------------------
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # REQUIRED: set in Render
GITHUB_REPO = os.getenv("GITHUB_REPO")    # e.g., "tuccijr75/Dr.-Feel-Good"
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")

GITHUB_API_BASE = f"https://api.github.com/repos/{GITHUB_REPO}/contents"
GH_HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}

# Quick guard so failures are explicit
def _require_env(varname):
    val = os.getenv(varname)
    if not val:
        raise RuntimeError(f"Missing required environment variable: {varname}")
    return val

# -------------------------------------------------
# Helpers: GitHub file read/write
# -------------------------------------------------
def gh_get_file(path: str):
    """Return (text, sha) or (None, None) if not found."""
    url = f"{GITHUB_API_BASE}/{path}"
    r = requests.get(url, headers=GH_HEADERS)
    if r.status_code == 200:
        blob = r.json()
        content = base64.b64decode(blob["content"]).decode("utf-8")
        return content, blob["sha"]
    return None, None

def gh_put_file(path: str, text: str, message: str, sha: str | None = None):
    """Create/update a text file at path with commit message."""
    encoded = base64.b64encode(text.encode("utf-8")).decode("utf-8")
    body = {"message": message, "content": encoded, "branch": GITHUB_BRANCH}
    if sha:
        body["sha"] = sha
    url = f"{GITHUB_API_BASE}/{path}"
    r = requests.put(url, headers=GH_HEADERS, json=body)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"GitHub write failed for {path}: {r.status_code} {r.text}")

def gh_append_json(path: str, new_entry: dict):
    """Append new_entry to a JSON array file at path (create if missing)."""
    current_text, sha = gh_get_file(path)
    if current_text:
        try:
            data = json.loads(current_text) or []
            if not isinstance(data, list):
                data = []
        except json.JSONDecodeError:
            data = []
    else:
        data, sha = [], None

    data.append(new_entry)
    pretty = json.dumps(data, indent=2)
    gh_put_file(path, pretty, f"Update {path}", sha)

def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

# -------------------------------------------------
# Health
# -------------------------------------------------
@app.route("/", methods=["GET"])
def health():
    return jsonify({"ok": True, "service": "Dr-Feel-Good API", "time": now_iso()})

# -------------------------------------------------
# Mood logs
# -------------------------------------------------
@app.route("/log-mood", methods=["POST"])
def log_mood():
    """
    Body: { "mood": <number|string>, "notes": <string optional> }
    Appends to logs/mood_log.json in GitHub
    """
    _require_env("GITHUB_TOKEN"); _require_env("GITHUB_REPO")
    body = (request.get_json(silent=True) or {})
    mood = body.get("mood")
    notes = body.get("notes", "")
    if mood is None:
        return jsonify({"error": "mood is required"}), 400
    entry = {"timestamp": now_iso(), "mood": str(mood), "notes": notes}
    gh_append_json("logs/mood_log.json", entry)
    return jsonify({"status": "success", "entry": entry})

@app.route("/get-moods", methods=["GET"])
def get_moods():
    """Returns array from logs/mood_log.json (or [])"""
    _require_env("GITHUB_TOKEN"); _require_env("GITHUB_REPO")
    text, _ = gh_get_file("logs/mood_log.json")
    return jsonify(json.loads(text) if text else [])

# -------------------------------------------------
# Reminders
# -------------------------------------------------
@app.route("/add-reminder", methods=["POST"])
def add_reminder():
    """
    Body: { "reminder": <string>, "due_date": <ISO 8601 string> }
    Appends to logs/reminders.json in GitHub
    """
    _require_env("GITHUB_TOKEN"); _require_env("GITHUB_REPO")
    body = (request.get_json(silent=True) or {})
    reminder = body.get("reminder")
    due_date = body.get("due_date")
    if not reminder or not due_date:
        return jsonify({"error": "reminder and due_date are required"}), 400
    rid = int(datetime.now(timezone.utc).timestamp())
    entry = {"id": rid, "reminder": reminder, "due_date": due_date, "status": "pending", "created": now_iso()}
    gh_append_json("logs/reminders.json", entry)
    return jsonify({"status": "success", "entry": entry})

@app.route("/get-reminders", methods=["GET"])
def get_reminders():
    """Returns array from logs/reminders.json (or [])"""
    _require_env("GITHUB_TOKEN"); _require_env("GITHUB_REPO")
    text, _ = gh_get_file("logs/reminders.json")
    return jsonify(json.loads(text) if text else [])

# (Optional future) mark done
@app.route("/complete-reminder/<int:rid>", methods=["POST"])
def complete_reminder(rid: int):
    """Body: { "status": "done" } — updates reminders.json entry by id"""
    _require_env("GITHUB_TOKEN"); _require_env("GITHUB_REPO")
    text, sha = gh_get_file("logs/reminders.json")
    if not text:
        return jsonify({"error": "no reminders found"}), 404
    try:
        items = json.loads(text)
    except json.JSONDecodeError:
        items = []
    updated = False
    for item in items:
        if item.get("id") == rid:
            item["status"] = "done"
            item["completed"] = now_iso()
            updated = True
            break
    if not updated:
        return jsonify({"error": f"reminder id {rid} not found"}), 404
    pretty = json.dumps(items, indent=2)
    gh_put_file("logs/reminders.json", pretty, f"Complete reminder {rid}", sha)
    return jsonify({"status": "success", "id": rid})

# -------------------------------------------------
# Homework & Reflection
# -------------------------------------------------
HOMEWORK = [
    "Write 3 things you’re grateful for.",
    "Do 2 minutes of slow, deep breathing.",
    "Take a 10-minute phone-free walk.",
    "Send a supportive message to someone.",
    "Write one positive thing about yourself.",
    "Drink a glass of water and stretch for 60 seconds.",
    "Name the feeling; name the need (1 line each).",
    "Tidy one small surface for 2 minutes.",
    "Box-breathing 4-4-4-4 for 5 cycles.",
    "Schedule a 5-minute break in your day.",
]

FAREWELL_KEYWORDS = [
    "bye","goodbye","see ya","see you","catch you later","later","take care","ciao","adios",
    "peace","peace out","farewell","talk soon","talk to you later","see you tomorrow",
    "see you later","until next time","night","goodnight","gn","gotta go","heading out",
    "i’m off","end chat","close session"
]

@app.route("/get-homework", methods=["POST"])
def get_homework():
    import random
    return jsonify({"homework": random.choice(HOMEWORK)})

@app.route("/get-reflection", methods=["POST"])
def get_reflection():
    """
    Body: { "userText": "<last user message>" }
    If farewell keyword is present, returns a short reflection prompt.
    """
    body = (request.get_json(silent=True) or {})
    msg = (body.get("userText") or "").lower()
    if any(k in msg for k in FAREWELL_KEYWORDS):
        return jsonify({
            "reflection": "Before you go: What’s one thing you learned about yourself today?"
        })
    return jsonify({"reflection": None})

# -------------------------------------------------
# DSM/ICD update check (API-based, no local paths)
# -------------------------------------------------
APA_DSM_PAGE = "https://www.psychiatry.org/psychiatrists/practice/dsm"
WHO_ICD_API  = "https://id.who.int/icd/release/11/mms"
WHO_ICD_HUMAN= "https://icd.who.int/en"

@app.route("/check-updates", methods=["POST"])
def check_updates():
    """
    Body: { "checkType": "DSM" | "ICD" }
    Returns current info and also refreshes DSM_ICD_Update_Notice.txt in repo.
    """
    _require_env("GITHUB_TOKEN"); _require_env("GITHUB_REPO")
    body = (request.get_json(silent=True) or {})
    check_type = (body.get("checkType") or "DSM").upper()

    dsm_line = "DSM-5-TR (2022) is the current APA Text Revision."
    icd_line = "ICD-11 release date: unknown"
    try:
        r = requests.get(WHO_ICD_API, timeout=10)
        if r.ok:
            data = r.json()
            rel = data.get("releaseDate")
            if rel:
                icd_line = f"ICD-11 latest release date: {rel}"
    except Exception as e:
        icd_line = f"ICD-11 check error: {e}"

    # Build/Write Notice file (text)
    now = now_iso()
    notice = (
        "=============================================\n"
        "🧾  Dr. Feel Good — DSM-5-TR / ICD-11 Update Notice\n"
        "=============================================\n\n"
        f"Last automatic check: {now}\n\n"
        "DSM-5-TR official reference page:\n"
        f"▶  {APA_DSM_PAGE}\n"
        "Latest confirmed release: DSM-5-TR (2022) Text Revision\n\n"
        "ICD-11 official reference:\n"
        f"▶  {WHO_ICD_HUMAN}\n"
        f"WHO API endpoint: {WHO_ICD_API}\n"
        f"{icd_line}\n\n"
        "----------------------------------------------------------\n"
        "Update procedure\n"
        "----------------------------------------------------------\n"
        "1. Review lines above; if newer versions appear, visit APA/WHO links.\n"
        "2. Update persona notes accordingly.\n"
        "3. Commit this notice file to preserve provenance.\n"
    )
    prev, sha = gh_get_file("DSM_ICD_Update_Notice.txt")
    gh_put_file("DSM_ICD_Update_Notice.txt", notice, "Refresh DSM/ICD notice", sha)

    if check_type == "ICD":
        return jsonify({"update": icd_line, "source": WHO_ICD_API})
    else:
        return jsonify({"update": dsm_line, "source": APA_DSM_PAGE})

# -------------------------------------------------
# Local dev runner (Render uses gunicorn)
# -------------------------------------------------
if __name__ == "__main__":
    # Local run only
    app.run(host="0.0.0.0", port=5000)
