#!/usr/bin/env bash
#
# uninstall.sh
#
# Removes the SRX Prometheus Exporter application and service.
# Configuration is preserved unless --purge is specified.
#

set -Eeuo pipefail

SERVICE_NAME="srx-exporter"
SERVICE_USER="srx-exporter"
SERVICE_GROUP="srx-exporter"
INSTALL_DIR="/opt/srx-collector"
CONFIG_DIR="/etc/srx-collector"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

PURGE=0
if [[ "${1:-}" == "--purge" ]]; then
    PURGE=1
elif [[ $# -gt 0 ]]; then
    echo "Usage: sudo ./uninstall.sh [--purge]" >&2
    exit 2
fi

if [[ "${EUID}" -ne 0 ]]; then
    echo "ERROR: Run as root: sudo ./uninstall.sh [--purge]" >&2
    exit 1
fi

systemctl disable --now "${SERVICE_NAME}" 2>/dev/null || true
rm -f "${SERVICE_FILE}"
systemctl daemon-reload
systemctl reset-failed "${SERVICE_NAME}" 2>/dev/null || true

rm -rf "${INSTALL_DIR}"

if [[ "${PURGE}" -eq 1 ]]; then
    rm -rf "${CONFIG_DIR}"
    echo "Configuration removed: ${CONFIG_DIR}"
else
    echo "Configuration preserved: ${CONFIG_DIR}"
fi

if id "${SERVICE_USER}" >/dev/null 2>&1; then
    userdel "${SERVICE_USER}" 2>/dev/null || true
fi

if getent group "${SERVICE_GROUP}" >/dev/null 2>&1; then
    groupdel "${SERVICE_GROUP}" 2>/dev/null || true
fi

echo "SRX Prometheus Exporter uninstalled."
