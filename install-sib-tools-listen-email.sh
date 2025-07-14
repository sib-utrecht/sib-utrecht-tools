#!/bin/sh

if ! GUNICORN_PATH=$(command -v gunicorn); then
    echo "Error: gunicorn is not installed or not in PATH. Please install it with 'pip install gunicorn' and try again." >&2
    exit 1
fi

read -p "Enter the user to run the service as: " SERVICE_USER
WORKDIR=$(pwd)
SERVICE_FILE=/etc/systemd/system/sib-tools-listen-email.service

echo "Using workdir: $WORKDIR"

read -p "Enter the location of the file which contains the keyring decrypt password: " KEYRING_ENV_FILE

cat <<EOF | sudo tee $SERVICE_FILE > /dev/null
[Unit]
Description=SIB Tools Flask SNS Email Listener (gunicorn)
After=network.target

[Service]
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$WORKDIR
ExecStart=$GUNICORN_PATH -w 1 -b 0.0.0.0:8087 sib_tools.listen_sns_for_email:app
Restart=always
Environment=PYTHONUNBUFFERED=1

# Load environment variables from secure file
EnvironmentFile=$KEYRING_ENV_FILE

# Security settings
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
#ProtectHome=yes
ReadWritePaths=$WORKDIR

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable sib-tools-listen-email
sudo systemctl restart sib-tools-listen-email
