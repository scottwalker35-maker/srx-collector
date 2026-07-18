# Grafana Dashboards

Place exported Grafana dashboard JSON files in this directory.

Recommended dashboard content:

- Hostname, management IP, model, Junos version, and serial number
- Exporter health
- MNHA active/backup/down state
- CPU utilization
- Memory utilization
- Active sessions
- Session capacity percentage
- Uptime in days with 270-day warning and 300-day critical threshold
- Interface receive and transmit throughput
- Interface errors and drops
- Collection duration and error count

## Suggested colors

MNHA:

- Active: green
- Backup or Standby: blue
- Down or Unknown: red

Exporter:

- Up: green
- Down: red

Uptime:

- Below 270 days: green
- 270 through 299 days: yellow
- 300 days or more: red

## Canvas field guidance

Use one Prometheus query per displayed value when units differ.

Set unique query legends to avoid ambiguous `Value` fields:

```text
Cpu98
Sessions98
UptimeDays98
HaRole98
```
