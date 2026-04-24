"""
server.py  –  Remote Monitor Backend
Receives activity reports from employee agents and serves them to the dashboard.

Install:  pip install flask flask-cors
Run:      python server.py

For production, run behind gunicorn:
    pip install gunicorn
    gunicorn -w 2 -b 0.0.0.0:8000 server:app
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime, timedelta
import os, json

app = Flask(__name__)
CORS(app)   # allow the HTML dashboard to call this API from any origin

# In-memory store.  Replace with SQLite for persistence across restarts.
employees = {}
screenshots = {}   # name → latest base64 JPEG

OFFLINE_AFTER_SECONDS = 90   # mark offline if no report for this long


def mark_offline():
    """Return employee data with status set to offline if stale."""
    cutoff = datetime.now() - timedelta(seconds=OFFLINE_AFTER_SECONDS)
    result = []
    for name, data in employees.items():
        d = dict(data)
        try:
            ts = datetime.fromisoformat(d["timestamp"])
            if ts < cutoff:
                d["status"]   = "offline"
                d["activity"] = 0
        except Exception:
            pass
        result.append(d)
    return result


# ── Receive report from agent ────────────────
@app.route("/report", methods=["POST"])
def receive_report():
    data = request.get_json(silent=True)
    if not data or "name" not in data:
        return jsonify({"error": "invalid payload"}), 400

    name = data["name"]

    # store screenshot separately (keeps the /status response small)
    if "screenshot" in data:
        screenshots[name] = {
            "image":     data.pop("screenshot"),
            "timestamp": data.get("timestamp", datetime.now().isoformat())
        }

    employees[name] = data
    return jsonify({"ok": True})


# ── Dashboard API ────────────────────────────
@app.route("/status", methods=["GET"])
def get_status():
    return jsonify(mark_offline())


@app.route("/screenshot/<name>", methods=["GET"])
def get_screenshot(name):
    shot = screenshots.get(name)
    if not shot:
        return jsonify({"error": "no screenshot yet"}), 404
    return jsonify(shot)


# ── Serve dashboard HTML (optional) ─────────
@app.route("/")
def dashboard():
    dashboard_path = os.path.join(os.path.dirname(__file__), "..", "dashboard")
    return send_from_directory(dashboard_path, "dashboard.html")


if __name__ == "__main__":
    print("Monitor server starting on http://0.0.0.0:8000")
    app.run(host="0.0.0.0", port=8000, debug=False)
