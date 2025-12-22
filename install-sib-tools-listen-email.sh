#!/bin/sh
set -e

# Set venv path
WORKDIR=/home/sib-tools/sib-utrecht-tools
VENV_PATH="$WORKDIR/.venv"
GUNICORN_PATH="$VENV_PATH/bin/gunicorn"
# GUNICORN_PATH="/usr/bin/gunicorn"
if [ ! -x "$GUNICORN_PATH" ]; then
    echo "Error: gunicorn is not installed at $GUNICORN_PATH" >&2
    # echo "Error: gunicorn is not installed in $VENV_PATH. Please install it with '. $VENV_PATH/bin/activate && pip install gunicorn' and try again." >&2
    exit 1
fi

# read -p "Enter the user to run the service as: " SERVICE_USER
SERVICE_USER=sib-tools

SERVICE_FILE=/etc/systemd/system/sib-tools-listen-email.service

echo "Using workdir: $WORKDIR"

# read -p "Enter the location of the file which contains the keyring decrypt password: " KEYRING_ENV_FILE
sudo mkdir -p /etc/sib-tools
KEYRING_ENV_FILE=/etc/sib-tools/keyring-decrypt-password.env

# Check if the keyring password file exists
if [ ! -f "$KEYRING_ENV_FILE" ]; then
    echo "File $KEYRING_ENV_FILE does not exist."
    read -p "Would you like to generate one? (y/n): " GENERATE_FILE
    if [ "$GENERATE_FILE" = "y" ] || [ "$GENERATE_FILE" = "Y" ]; then
        # Generate a random password (32 characters, alphanumeric)
        RANDOM_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
        echo "KEYRING_CRYPTFILE_PASSWORD=\"$RANDOM_PASSWORD\"" > "$KEYRING_ENV_FILE"
        sudo chmod 600 "$KEYRING_ENV_FILE"
        sudo chown sib-tools "$KEYRING_ENV_FILE"
        echo "Generated keyring password file at $KEYRING_ENV_FILE"
        echo "Password has been set. Please keep this file secure."
    else
        echo "Cannot proceed without keyring password file. Exiting."
        exit 1
    fi
fi

cat <<EOF | sudo tee $SERVICE_FILE > /dev/null
[Unit]
Description=SIB Tools Flask SNS Email Listener (gunicorn)
After=network.target

[Service]
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$WORKDIR
ExecStart=/usr/bin/uv run gunicorn -w 1 -b 0.0.0.0:8087 sib_tools.listen_sns_for_email:app
Restart=always
Environment=PYTHONUNBUFFERED=1
Environment=PATH=$VENV_PATH/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

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
