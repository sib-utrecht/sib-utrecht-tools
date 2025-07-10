#!/bin/sh

if ! GUNICORN_PATH=$(command -v gunicorn); then
    echo "Error: gunicorn is not installed or not in PATH. Please install it with 'pip install gunicorn' and try again." >&2
    exit 1
fi

WORKDIR=$(pwd)

mkdir -p ~/.config/systemd/user
cat <<EOF > ~/.config/systemd/user/sib-tools-listen-email.service
[Unit]
Description=SIB Tools Flask SNS Email Listener (gunicorn)
After=network.target

[Service]
WorkingDirectory=$WORKDIR
ExecStart=$GUNICORN_PATH -w 1 -b 127.0.0.1:8087 sib_tools.serve:app
Restart=always
Environment=PYTHONUNBUFFERED=1
Environment=PYTHONPATH=$WORKDIR

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now sib-tools-listen-email