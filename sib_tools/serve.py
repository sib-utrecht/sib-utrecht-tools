from flask import Flask, request
import sys
import json
from sib_tools.email.forms_extract_mail import (
    extract_fields_from_mail,
    form_to_canonical,
)
import tempfile
import os
from datetime import datetime, timezone

app = Flask(__name__)


@app.route("/sns-incoming", methods=["POST"])
def sns_incoming():
    # SNS sends a JSON payload
    data = request.get_json(force=True)
    print(f"Received request. Length: {request.content_length} bytes")
    with open("sns_incoming.log", "a") as log_file:
        log_file.write(
            f"[{datetime.now(timezone.utc).astimezone().isoformat()}] Received data: {json.dumps(data)}\n"
        )
        log_file.write(
            f"[{datetime.now(timezone.utc).astimezone().isoformat()}]\n"
        )

    # print(f"Received data: {json.dumps(data)}")
    print()
    # Handle SNS subscription confirmation
    if "Type" in data and data["Type"] == "SubscriptionConfirmation":
        # Confirm the subscription by visiting the SubscribeURL
        import requests

        try:
            requests.get(data["SubscribeURL"])
        except Exception as e:
            print(f"Failed to confirm subscription: {e}", file=sys.stderr)
        return "", 200
    # Handle notification
    if "Type" in data and data["Type"] == "Notification":
        # The actual e-mail content is usually in data['Message']
        message = data["Message"]
        # Save to a temp file and process as .eml
        with tempfile.NamedTemporaryFile(delete=False, suffix=".eml") as tmp:
            tmp.write(message.encode("utf-8"))
            tmp_path = tmp.name
        print(f"Temporary file created at: {tmp_path}")
        # try:
        #     fields = extract_fields_from_mail(tmp_path)
        #     canonical = form_to_canonical(fields)
        #     print(json.dumps(canonical, indent=2))
        # except Exception as e:
        #     print(f"Failed to process e-mail: {e}", file=sys.stderr)
        # finally:
        #     os.unlink(tmp_path)
        return "", 200
    return "", 400


def run_email_listener(host="127.0.0.1", port=8087):
    app.run(host=host, port=port)
