# Juniper SRX NETCONF Prometheus Exporter

A modular Python exporter that collects operational data from Juniper SRX and
vSRX firewalls through NETCONF and exposes the latest values in Prometheus
format.

The exporter is designed for SRX monitoring in standalone, virtual, and
Multi-Node High Availability deployments. Grafana, Alertmanager, or any other
Prometheus-compatible consumer may use the exported metrics, but dashboard
implementation is outside this repository's core scope.

## Current collectors

- System information
- Multi-Node High Availability status
- Security flow session summary
- Routing Engine statistics
- Physical and logical interface statistics
- Security Screen IDS counters
- Security policy hit counters

The Security Screen collector supports a configurable list of zones.

The security policy hit-count collector discovers every policy returned by
Junos. Adding, deleting, or renaming an SRX policy does not require a Python
code change.

## Project layout

```text
srx-collector/
├── collector.py
├── exporter.py
├── config.yaml
├── config.example.yaml
├── requirements.txt
├── AI_COLLECTOR_INSTRUCTIONS.md
├── collectors/
│   ├── system.py
│   ├── ha.py
│   ├── sessions.py
│   ├── route_engine.py
│   ├── interface_statistics.py
│   ├── security_screen.py
│   └── security_policy_hit_count.py
├── exporters/
│   └── prometheus.py
├── lib/
│   └── netconf.py
├── docs/
│   ├── architecture.md
│   ├── collectors.md
│   └── metrics.md
└── scripts/
    └── export_ai_collector_context.sh
```

## Requirements

- Linux
- Python 3.10 or newer
- NETCONF over SSH enabled on the SRX
- TCP port 830 reachable from the exporter host
- A Junos account allowed to execute the required operational RPCs

Basic Junos configuration:

```text
set system services netconf ssh
```

## Installation

```bash
cd ~/srx-collector

python3 -m venv venv
source venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt

cp config.example.yaml config.yaml
nano config.yaml
chmod 600 config.yaml
```

Never commit the live `config.yaml` file.

## Configuration example

```yaml
exporter:
  listen_address: 0.0.0.0
  listen_port: 9105
  collection_interval_seconds: 30

devices:
  - name: R3KL4W-vFW-01
    host: 192.0.2.10
    port: 830
    username: netconf-user
    password: CHANGE_ME

    interfaces:
      - ge-0/0/0
      - ge-0/0/1
      - fxp0
      - st0

    security_screen_zones:
      - untrust
```

Selecting a parent interface includes its logical units.

Every zone listed under `security_screen_zones` is queried independently.

Security policies do not need to be listed. They are dynamically discovered
through:

```xml
<get-security-policies-hit-count/>
```

## Run locally

Command-line collector:

```bash
source venv/bin/activate
python collector.py
```

Prometheus exporter:

```bash
source venv/bin/activate
python exporter.py
```

Verify the endpoint:

```bash
curl -s http://127.0.0.1:9105/metrics |
grep '^srx_'
```

Default endpoint:

```text
http://0.0.0.0:9105/metrics
```

## Prometheus scrape configuration

```yaml
scrape_configs:
  - job_name: juniper_netconf
    static_configs:
      - targets:
          - 127.0.0.1:9105
```

## New collector workflow

The repository includes an LLM-specific implementation guide:

```text
AI_COLLECTOR_INSTRUCTIONS.md
```

It is intended to be pasted into ChatGPT or another LLM together with:

1. the Junos `| display xml` output;
2. the Junos `| display xml rpc` output;
3. the generated repository context.

Generate the repository context with:

```bash
./scripts/export_ai_collector_context.sh
```

See [Collectors](docs/collectors.md) for the human-readable collector
inventory and [Metrics](docs/metrics.md) for exported metric conventions.

- Added system_alarms collector: exports srx_system_alarm_active_count, srx_system_alarm_active, and srx_system_alarm_raised_timestamp_seconds from 'show system alarms' (get-system-alarm-information).

### IKE security associations

The exporter dynamically collects all entries returned by
`show security ike security-associations`. Metrics include both the NETCONF
device and Junos firewall hostname.

### IKE security-association detail

The exporter dynamically discovers current IKE indices and collects each
association with:

```text
show security ike security-associations detail index <index>
```

Every metric includes the configured NETCONF `device`, Junos `firewall`
hostname, and current `ike_index`.

### IPsec security associations

The exporter dynamically collects every entry returned by:

```text
show security ipsec security-associations
```

Every metric includes the configured NETCONF `device` and Junos `firewall`
hostname. Tunnel indices are retained for current-state correlation and later
detail collection.

### IPsec security-association detail

The exporter dynamically discovers current IPsec tunnel indices and collects
each tunnel with `show security ipsec security-associations detail index
<index>`. Metrics are linked to the NETCONF device, Junos hostname, tunnel
index, VPN name, remote gateway, and bind interface.
