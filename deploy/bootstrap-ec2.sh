#!/usr/bin/env bash
# Prepare Ubuntu once; CI starts the API after publishing an approved model.
set -euo pipefail

if [[ $# -ne 3 || ${EUID} -ne 0 ]]; then
    echo 'Usage: sudo bash bootstrap-ec2.sh BUCKET AWS_REGION VM_USER' >&2
    exit 1
fi
bucket="$1"
region="$2"
vm_user="$3"
if [[ ! "$bucket" =~ ^[a-z0-9][a-z0-9.-]+[a-z0-9]$ || ! "$region" =~ ^[a-z0-9-]+$ || ! "$vm_user" =~ ^[a-z_][a-z0-9_-]*$ ]]; then
    echo 'Invalid bucket, region or username' >&2
    exit 1
fi
vm_home="$(getent passwd "$vm_user" | cut -d: -f6)"
if [[ -z "$vm_home" || "$vm_home" != /home/* ]]; then
    echo 'Expected an existing deployment user with a home under /home' >&2
    exit 1
fi
apt-get update
apt-get install -y python3-venv curl
install -d -o "$vm_user" -g "$vm_user" "$vm_home/models" "$vm_home/src"
sudo -u "$vm_user" python3 -m venv "$vm_home/.venv"
cat > "$vm_home/income-api.env" <<EOF
ARTIFACT_BUCKET=$bucket
AWS_DEFAULT_REGION=$region
MODEL_PATH=$vm_home/models/model.joblib
EOF
chown "$vm_user:$vm_user" "$vm_home/income-api.env"
chmod 600 "$vm_home/income-api.env"
cat > /etc/systemd/system/income-api.service <<EOF
[Unit]
Description=Adult Income Model Inference API
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=$vm_user
WorkingDirectory=$vm_home
EnvironmentFile=$vm_home/income-api.env
ExecStart=$vm_home/.venv/bin/python $vm_home/src/serve.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
# Allow only the service restart operation used by CI.
printf '%s ALL=(root) NOPASSWD: /usr/bin/systemctl restart income-api\n' "$vm_user" > /etc/sudoers.d/income-api
chmod 440 /etc/sudoers.d/income-api
visudo -cf /etc/sudoers.d/income-api
systemctl daemon-reload
systemctl enable income-api
echo 'EC2 prepared. CI installs dependencies and starts the API after the quality gate passes.'
