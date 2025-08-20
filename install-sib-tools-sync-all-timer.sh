#!/bin/sh

# Install a systemd service + timer to run `sib-tools sync all` daily
set -e

read -p "Enter the user to run the service as: " SERVICE_USER
WORKDIR=$(pwd)
SERVICE_FILE=/etc/systemd/system/sib-tools-sync-all.service
TIMER_FILE=/etc/systemd/system/sib-tools-sync-all.timer

echo "Using workdir: $WORKDIR"

read -p "Enter the location of the file which contains the keyring decrypt password: " KEYRING_ENV_FILE

# Create service unit (oneshot)
cat <<EOF | sudo tee $SERVICE_FILE > /dev/null
[Unit]
Description=SIB Tools daily sync (sib-tools sync all)
After=network.target

[Service]
Type=oneshot
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$WORKDIR
# Ensure venv/bin is preferred if present
Environment=PYTHONUNBUFFERED=1
Environment=PATH=$WORKDIR/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=python -m sib_tools sync all --mail-output

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

# Create timer unit (daily)
cat <<EOF | sudo tee $TIMER_FILE > /dev/null
[Unit]
Description=Run SIB Tools daily sync

[Timer]
# Run every day at 10:17.
OnCalendar=10:17
# Make up for missed runs if the machine was off
Persistent=false
# Add a small random delay to avoid thundering herd
RandomizedDelaySec=15m

[Install]
WantedBy=timers.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable sib-tools-sync-all.timer
sudo systemctl start sib-tools-sync-all.timer

echo "Installed and started sib-tools-sync-all.timer."
echo "Check with: systemctl status sib-tools-sync-all.timer && systemctl list-timers | grep sib-tools-sync-all"
