#!/usr/bin/env python3
"""
Slack Interactive Message Server

This server handles button clicks from Slack interactive messages.
When a user clicks a "Book" button, it triggers the booking workflow.

Requirements:
1. Create a Slack App at https://api.slack.com/apps
2. Enable "Interactivity" and set the Request URL to your server
3. Install the app to your workspace
4. Set SLACK_SIGNING_SECRET in .env

To run locally with ngrok:
1. pip install flask
2. python slack_server.py  (runs on port 5000)
3. ngrok http 5000  (in another terminal)
4. Copy the ngrok URL to Slack App's Interactivity Request URL
"""

print("=== slack_server.py starting ===", flush=True)

import os
import json
import hmac
import hashlib
import time
import asyncio
import threading
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

# Create session file from environment variable (for Railway deployment)
# This allows us to store the session as a secret and write it to a file at runtime
SESSION_DIR = Path(__file__).parent / "session_data"
SKEDDA_SESSION = os.environ.get("SKEDDA_SESSION", "")

if SKEDDA_SESSION:
    SESSION_DIR.mkdir(exist_ok=True)
    session_file = SESSION_DIR / "auth.json"
    session_file.write_text(SKEDDA_SESSION)
    print(f"Session file created at {session_file}")
else:
    print("Warning: SKEDDA_SESSION not set - booking will fail without session data")

app = Flask(__name__)

# Slack signing secret for request verification
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET", "")

def verify_slack_signature(request):
    """Verify that the request came from Slack."""
    if not SLACK_SIGNING_SECRET:
        print("Warning: SLACK_SIGNING_SECRET not set, skipping verification")
        return True

    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")

    # Check timestamp to prevent replay attacks (allow 5 min window)
    if abs(time.time() - int(timestamp)) > 60 * 5:
        return False

    # Compute signature
    sig_basestring = f"v0:{timestamp}:{request.get_data(as_text=True)}"
    my_signature = "v0=" + hmac.new(
        SLACK_SIGNING_SECRET.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(my_signature, signature)


def send_slack_response(response_url: str, message: str, replace_original: bool = False):
    """Send a response back to Slack."""
    import requests

    payload = {
        "text": message,
        "replace_original": replace_original
    }

    response = requests.post(response_url, json=payload)
    return response.status_code == 200


def run_booking_in_background(date_str: str, court: str, time_slot: str, user_name: str, response_url: str):
    """Run the booking process in a background thread."""
    def do_booking():
        from sniper import book_slot_direct

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success, message = loop.run_until_complete(
                book_slot_direct(date_str, court, time_slot)
            )
            loop.close()

            if success:
                send_slack_response(
                    response_url,
                    f"✅ *Booking Confirmed!*\n*Court:* {court}\n*Time:* {time_slot}\n*Date:* {date_str}\n\nBooked by @{user_name}",
                    replace_original=False
                )
            else:
                send_slack_response(
                    response_url,
                    f"❌ *Booking Failed*\n{message}\n\nPlease try booking manually.",
                    replace_original=False
                )
        except Exception as e:
            print(f"Booking error: {str(e)}")
            send_slack_response(
                response_url,
                f"❌ *Error:* {str(e)}",
                replace_original=False
            )

    thread = threading.Thread(target=do_booking)
    thread.start()


@app.route("/", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "ok", "version": "v2-threading", "message": "Slack Interactive Server is running"})


@app.route("/slack/actions", methods=["POST"])
def handle_slack_action():
    """Handle interactive message actions from Slack."""

    # Verify the request came from Slack
    if not verify_slack_signature(request):
        return jsonify({"error": "Invalid signature"}), 403

    # Parse the payload
    payload = json.loads(request.form.get("payload", "{}"))
    action_type = payload.get("type")

    if action_type == "block_actions":
        # Get the action details
        actions = payload.get("actions", [])
        user = payload.get("user", {})
        response_url = payload.get("response_url", "")

        for action in actions:
            action_id = action.get("action_id", "")
            value = action.get("value", "")

            if action_id.startswith("book_slot_"):
                # Parse the booking details from value: "date|court|time"
                parts = value.split("|")
                if len(parts) == 3:
                    date_str, court, time_slot = parts
                    user_name = user.get("name", "Unknown")

                    print(f"Booking request from {user_name}: {court} at {time_slot} on {date_str}")

                    # Start booking in background thread (don't block the response)
                    run_booking_in_background(date_str, court, time_slot, user_name, response_url)

                    # Return immediately to Slack (within 3 seconds)
                    return jsonify({
                        "response_type": "in_channel",
                        "text": f"⏳ Booking *{court}* at *{time_slot}* on *{date_str}*...\nRequested by @{user_name}"
                    })

    # Default response
    return jsonify({"response_type": "ephemeral", "text": "Action received"})


@app.route("/slack/events", methods=["POST"])
def handle_slack_event():
    """Handle Slack Events API (for URL verification)."""
    data = request.json

    # URL verification challenge
    if data.get("type") == "url_verification":
        return jsonify({"challenge": data.get("challenge")})

    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║         Slack Interactive Message Server                      ║
╠══════════════════════════════════════════════════════════════╣
║  Running on: http://localhost:{port}                           ║
║                                                               ║
║  Endpoints:                                                   ║
║    GET  /              - Health check                         ║
║    POST /slack/actions - Interactive message callbacks        ║
║    POST /slack/events  - Events API (URL verification)        ║
║                                                               ║
║  To expose to internet, use ngrok:                            ║
║    ngrok http {port}                                           ║
║                                                               ║
║  Then set in Slack App:                                       ║
║    Interactivity Request URL: https://xxx.ngrok.io/slack/actions║
╚══════════════════════════════════════════════════════════════╝
    """)

    app.run(host="0.0.0.0", port=port, debug=True)
