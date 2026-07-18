# systemd Service

## Example service

Create:

```text
/etc/systemd/system/srx-exporter.service
```

Contents:

```ini
[Unit]
Description=Juniper SRX NETCONF Prometheus Exporter
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=walkersc
Group=walkersc
WorkingDirectory=/home/walkersc/srx-collector
ExecStart=/home/walkersc/srx-collector/venv/bin/python /home/walkersc/srx-collector/exporter.py
Restart=on-failure
RestartSec=10
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

Adjust the username and paths for the target host.

## Install and start

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now srx-exporter
```

## Status and logs

```bash
sudo systemctl status srx-exporter --no-pager
sudo journalctl -u srx-exporter -f
```

## Restart after code changes

```bash
sudo systemctl restart srx-exporter
```

## Validate endpoint

```bash
curl -s http://localhost:9105/metrics |
grep '^srx_exporter_up'
```
