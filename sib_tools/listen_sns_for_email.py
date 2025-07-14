from flask import Flask, request
import sys
import json

import tempfile
import os
from datetime import datetime, timezone
import base64
import urllib.request
import hashlib
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
import re
import boto3
import traceback
from pathlib import Path


from .aws.auth import get_s3_client
from .email.process_elm_file import process_email

from .auth import check_available_auth, configure_keyring
configure_keyring()

# Make sure you have install the following packages:
# sudo pip install gunicorn
# pip install flask
# pip install beautifulsoup4

print("Initializing Flask app for SNS incoming emails...")
app = Flask(__name__)

AUTOCONFIRM_SUBSCRIPTION = False

mail_output_dir = Path.cwd() / "mails"

# Do credentials check print
print("Available credentials:")
check_available_auth(non_interactive=True)


@app.route("/sns-incoming", methods=["POST"])
def sns_incoming():
    # SNS sends a JSON payload
    data = request.get_json(force=True)
    print(f"Received request. Length: {request.content_length} bytes")
    with open("sns_incoming.log", "a") as log_file:
        log_file.write(f"[{datetime.now(timezone.utc).astimezone().isoformat()}]\n")
        log_file.write(
            f"[{datetime.now(timezone.utc).astimezone().isoformat()}] Received data: {json.dumps(data)}\n"
        )

    print()
    if not verify_sns_signature(data):
        print("SNS signature verification failed or not authentic.", file=sys.stderr)
        return "", 403
    if "Type" in data and data["Type"] == "SubscriptionConfirmation":
        subscription_url = data.get("SubscribeURL")

        print(f"Received SubscriptionConfirmation for {data.get('TopicArn')}.")
        print(f"SubscribeURL: {subscription_url}")

        if not AUTOCONFIRM_SUBSCRIPTION:
            print("Not automatically confirming. Use the url to confirm")
            return "", 200

        if AUTOCONFIRM_SUBSCRIPTION:
            # Confirm the subscription by visiting the SubscribeURL
            import requests

            try:
                requests.get(data["SubscribeURL"])
                print("Executed confirmation request")
            except Exception as e:
                print(f"Failed to confirm subscription: {e}", file=sys.stderr)
            return "", 200
        
    # Handle notification
    if "Type" in data and data["Type"] == "Notification":
        # The message contains the header of the e-mail and where it is stored,
        # but not the body
        message = json.loads(data["Message"])

        mail = message.get("mail", {})
        receipt = message.get("receipt", {})

        is_valid = (
            (
                mail.get("source") == "info@sib-utrecht.nl"
                or mail.get("source") == "secretaris@sib-utrecht.nl"
            )
            and receipt.get("spfVerdict", {}).get("status") == "PASS"
            and receipt.get("dkimVerdict", {}).get("status") == "PASS"
            and receipt.get("dmarcVerdict", {}).get("status") == "PASS"
        )

        if not is_valid:
            print("Sender is not authorized")
            return "", 200
        
        notification_type = message.get("notificationType", "Unknown")
        print(f"Notification type: {notification_type}")

        if notification_type != "Received":
            print(f"Unexpected notification type: {notification_type}", file=sys.stderr)
            return "", 200
        
        action = receipt.get("action")
        if action is None:
            print("No action specified in receipt", file=sys.stderr)
            return "", 200
        
        bucket_name = action.get("bucketName")
        objectKey = action.get("objectKey")

        if bucket_name is None or objectKey is None:
            print("Missing bucketName or objectKey in receipt", file=sys.stderr)
            return "", 200
        
        print(f"Processing e-mail from bucket '{bucket_name}' with key '{objectKey}'")

        objectKeyStem = objectKey.split("/")[-1]

        filename = f"{receipt.get('timestamp')[:16].replace('T', '_')}_{objectKeyStem}.eml"
        mail_output_path = mail_output_dir / filename

        # Save to a temp file and process as .eml
        # with tempfile.NamedTemporaryFile(delete=False, suffix=".eml") as tmp:
        #     tmp_path = tmp.name

        # Download the e-mail from the S3 bucket
        try:
            s3_client = get_s3_client()
            mail_output_path.parent.mkdir(parents=True, exist_ok=True)
            s3_client.download_file(bucket_name, objectKey, mail_output_path)

            print(f"Downloaded e-mail to {mail_output_path}")
            with open("sns_incoming.log", "a") as log_file:
                log_file.write(f"Mail output path: {mail_output_path}\n")

            # Process the downloaded e-mail
            process_email(mail_output_path)

        except Exception as e:
            print(f"Failed to process e-mail: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
        return "", 200
    return "", 400


def run_email_listener(host="127.0.0.1", port=8087):
    app.run(host=host, port=port)


def verify_sns_signature(data):
    # Only verify Notification and SubscriptionConfirmation
    if data.get("Type") not in ("Notification", "SubscriptionConfirmation"):
        return False
    # Get the signing cert URL
    cert_url = data.get("SigningCertURL")
    # Strict validation for AWS SNS cert URL
    pattern = re.compile(
        r"^https://sns\.[a-z0-9_-]+\.amazonaws\.com/SimpleNotificationService-[a-zA-Z0-9_-]+\.pem$"
    )
    if not cert_url or not pattern.match(cert_url):
        print(f"Invalid SigningCertURL: {cert_url}", file=sys.stderr)
        return False
    # Download the certificate
    with urllib.request.urlopen(cert_url) as response:
        cert_pem = response.read()
    cert = x509.load_pem_x509_certificate(cert_pem, default_backend())
    public_key = cert.public_key()
    # Build the string to sign
    fields = []
    if data["Type"] == "Notification":
        fields = [
            ("Message", data["Message"]),
            ("MessageId", data["MessageId"]),
        ]
        if "Subject" in data:
            fields.append(("Subject", data["Subject"]))
        fields += [
            ("Timestamp", data["Timestamp"]),
            ("TopicArn", data["TopicArn"]),
            ("Type", data["Type"]),
        ]
    elif data["Type"] == "SubscriptionConfirmation":
        fields = [
            ("Message", data["Message"]),
            ("MessageId", data["MessageId"]),
            ("SubscribeURL", data["SubscribeURL"]),
            ("Timestamp", data["Timestamp"]),
            ("Token", data["Token"]),
            ("TopicArn", data["TopicArn"]),
            ("Type", data["Type"]),
        ]
    string_to_sign = ""
    for k, v in fields:
        string_to_sign += f"{k}\n{v}\n"
    # Decode the signature
    signature = base64.b64decode(data["Signature"])
    # Verify the signature
    try:
        public_key.verify(
            signature, string_to_sign.encode("utf-8"), padding.PKCS1v15(), hashes.SHA1()
        )
        print("Successfully verified SNS signature.")
        return True
    except Exception as e:
        print(f"SNS signature verification failed: {e}", file=sys.stderr)
        return False
