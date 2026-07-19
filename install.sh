#!/usr/bin/env bash
#
# install.sh
#
# Fresh install or upgrade of the Juniper SRX NETCONF Prometheus Exporter.
#
# Production layout:
#   Application:   /opt/srx-collector
#   Configuration: /etc/srx-collector/config.yaml
#   Service:       /etc/systemd/system/srx-exporter.service
#   Account:       srx-exporter
#

set -Eeuo pipefail
IFS=$'\n\t'

SERVICE_NAME="srx-exporter"
SERVICE_USER="srx-exporter"
SERVICE_GROUP="srx-exporter"

INSTALL_DIR="/opt/srx-collector"
CONFIG_DIR="/etc/srx-collector"
CONFIG_FILE="${CONFIG_DIR}/config.yaml"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
VENV_DIR="${INSTALL_DIR}/venv"
METRICS_URL="${METRICS_URL:-http://127.0.0.1:9105/metrics}"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

log() {
    printf '\n[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

warn() {
    printf '\nWARNING: %s\n' "$*" >&2
}

die() {
    printf '\nERROR: %s\n' "$*" >&2
    exit 1
}

on_error() {
    local exit_code=$?
    printf '\nERROR: Installation failed at line %s (exit code %s).\n' \
        "${BASH_LINENO[0]:-unknown}" "$exit_code" >&2
    exit "$exit_code"
}

trap on_error ERR

if [[ "${EUID}" -ne 0 ]]; then
    die "Run this installer as root: sudo ./install.sh"
fi

if [[ ! -f "${SCRIPT_DIR}/requirements.txt" ]]; then
    die "requirements.txt was not found in ${SCRIPT_DIR}"
fi

if [[ ! -f "${SCRIPT_DIR}/exporter.py" ]]; then
    die "exporter.py was not found in ${SCRIPT_DIR}"
fi

if [[ ! -f "${SCRIPT_DIR}/config.example.yaml" ]]; then
    die "config.example.yaml was not found in ${SCRIPT_DIR}"
fi

printf '%s\n' \
    "========================================" \
    " SRX Prometheus Exporter Installer" \
    "========================================" \
    "" \
    "Source:        ${SCRIPT_DIR}" \
    "Install path:  ${INSTALL_DIR}" \
    "Configuration: ${CONFIG_FILE}" \
    "Service:       ${SERVICE_NAME}"

log "Installing operating-system dependencies"
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y \
    ca-certificates \
    curl \
    python3 \
    python3-pip \
    python3-venv \
    rsync

log "Creating service account"
if ! getent group "${SERVICE_GROUP}" >/dev/null 2>&1; then
    groupadd --system "${SERVICE_GROUP}"
fi

if ! id "${SERVICE_USER}" >/dev/null 2>&1; then
    useradd \
        --system \
        --gid "${SERVICE_GROUP}" \
        --home-dir "${INSTALL_DIR}" \
        --no-create-home \
        --shell /usr/sbin/nologin \
        "${SERVICE_USER}"
fi

log "Creating installation directories"
install -d -o root -g root -m 0755 "${INSTALL_DIR}"
install -d -o root -g "${SERVICE_GROUP}" -m 0750 "${CONFIG_DIR}"

log "Stopping the service during upgrade, if currently installed"
if systemctl list-unit-files "${SERVICE_NAME}.service" >/dev/null 2>&1; then
    systemctl stop "${SERVICE_NAME}" || true
fi

log "Copying application files"
rsync -a --delete \
    --exclude '.git/' \
    --exclude '.github/' \
    --exclude '.idea/' \
    --exclude '.vscode/' \
    --exclude '__pycache__/' \
    --exclude '*.pyc' \
    --exclude '*.pyo' \
    --exclude 'venv/' \
    --exclude '.venv/' \
    --exclude 'backup/' \
    --exclude 'backups/' \
    --exclude 'config.yaml' \
    --exclude '*.log' \
    "${SCRIPT_DIR}/" "${INSTALL_DIR}/"

log "Installing configuration"
if [[ ! -f "${CONFIG_FILE}" ]]; then
    install -o root -g "${SERVICE_GROUP}" -m 0640 \
        "${SCRIPT_DIR}/config.example.yaml" "${CONFIG_FILE}"
    CONFIG_CREATED=1
else
    chown root:"${SERVICE_GROUP}" "${CONFIG_FILE}"
    chmod 0640 "${CONFIG_FILE}"
    CONFIG_CREATED=0
fi

# Compatibility with the current exporter, which expects config.yaml in its
# working directory. The real file remains safely under /etc.
ln -sfn "${CONFIG_FILE}" "${INSTALL_DIR}/config.yaml"

log "Creating Python virtual environment"
if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
    rm -rf "${VENV_DIR}"
    python3 -m venv "${VENV_DIR}"
fi

log "Installing Python dependencies"
"${VENV_DIR}/bin/python" -m pip install --upgrade pip setuptools wheel
"${VENV_DIR}/bin/python" -m pip install --upgrade -r "${INSTALL_DIR}/requirements.txt"

log "Applying ownership and permissions"
chown -R root:root "${INSTALL_DIR}"
find "${INSTALL_DIR}" -type d -exec chmod 0755 {} +
find "${INSTALL_DIR}" -type f -exec chmod 0644 {} +
chmod 0755 "${INSTALL_DIR}/install.sh" 2>/dev/null || true
chmod 0755 "${INSTALL_DIR}/uninstall.sh" 2>/dev/null || true
chmod -R a+rX "${VENV_DIR}"
chown -h root:"${SERVICE_GROUP}" "${INSTALL_DIR}/config.yaml"

log "Installing systemd service"
cat > "${SERVICE_FILE}" <<EOF
[Unit]
Description=Juniper SRX NETCONF Prometheus Exporter
Documentation=https://github.com/
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_GROUP}
WorkingDirectory=${INSTALL_DIR}
ExecStart=${VENV_DIR}/bin/python ${INSTALL_DIR}/exporter.py
Restart=on-failure
RestartSec=10
TimeoutStopSec=30
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true
ReadWritePaths=${CONFIG_DIR}

[Install]
WantedBy=multi-user.target
EOF

chmod 0644 "${SERVICE_FILE}"

log "Reloading systemd and enabling the service"
systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"

if [[ "${CONFIG_CREATED}" -eq 1 ]]; then
    warn "A new configuration file was created at ${CONFIG_FILE}."
    warn "Edit it before expecting successful SRX collection."
fi

log "Starting the service"
systemctl restart "${SERVICE_NAME}"

log "Checking service status"
sleep 3
if ! systemctl is-active --quiet "${SERVICE_NAME}"; then
    systemctl status "${SERVICE_NAME}" --no-pager || true
    journalctl -u "${SERVICE_NAME}" -n 50 --no-pager || true
    die "${SERVICE_NAME} failed to start"
fi

log "Checking metrics endpoint"
METRICS_OK=0
for _ in {1..10}; do
    if curl --silent --show-error --fail --max-time 3 \
        "${METRICS_URL}" >/dev/null 2>&1; then
        METRICS_OK=1
        break
    fi
    sleep 2
done

printf '\n========================================\n'
printf ' Installation complete\n'
printf '========================================\n'
printf 'Application:   %s\n' "${INSTALL_DIR}"
printf 'Configuration: %s\n' "${CONFIG_FILE}"
printf 'Service:       %s\n' "${SERVICE_NAME}"

if [[ "${METRICS_OK}" -eq 1 ]]; then
    printf 'Metrics:       %s (responding)\n' "${METRICS_URL}"
else
    warn "The service is running, but ${METRICS_URL} did not respond yet."
    warn "Check the configuration and logs."
fi

printf '\nUseful commands:\n'
printf '  sudo nano %s\n' "${CONFIG_FILE}"
printf '  sudo systemctl restart %s\n' "${SERVICE_NAME}"
printf '  sudo systemctl status %s\n' "${SERVICE_NAME}"
printf '  sudo journalctl -u %s -f\n' "${SERVICE_NAME}"
printf '  curl %s\n' "${METRICS_URL}"
