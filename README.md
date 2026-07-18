# Juniper SRX NETCONF Prometheus Exporter

A modular Python exporter that collects operational data from Juniper SRX and
vSRX firewalls over NETCONF and exposes the results in Prometheus format for
Grafana dashboards and alerting.

## Why this project exists

The project provides a practical alternative to legacy SNMP polling where
faster collection intervals, richer Junos operational data, and modern
Prometheus/Grafana integration are required.

Current goals:

- collect SRX operational data through Junos NETCONF RPCs;
- poll at configurable intervals such as 30 or 60 seconds;
- expose numeric values as Prometheus metrics;
- expose identity and state strings as Prometheus labels;
- keep each Junos feature in a separate collector module;
- remain easy to extend with additional collectors.

## Current collectors

- System information
- Multi-Node High Availability information
- Security flow session summary
- Routing Engine CPU, memory, load, reboot, and uptime information
- Selected physical and logical interface statistics

Planned collectors may include:

- SPU utilization
- IPsec and IKE
- NAT
- Security policy counters
- BGP and OSPF
- Alarms and environmental sensors

## Project layout

```text
srx-collector/
├── collector.py
├── exporter.py
├── config.yaml
├── config.example.yaml
├── requirements.txt
├── collectors/
│   ├── system.py
│   ├── ha.py
│   ├── sessions.py
│   ├── route_engine.py
│   └── interface_statistics.py
├── exporters/
│   └── prometheus.py
├── lib/
│   └── netconf.py
├── docs/
├── dashboards/
└── AI_HELP.md
```

## Requirements

- Linux
- Python 3.10 or newer
- Junos NETCONF enabled on each SRX
- TCP port 830 reachable from the exporter host
- A Junos account with permission to execute the required operational RPCs

## Junos configuration

A basic NETCONF configuration normally includes:

```text
set system services netconf ssh
```

Use an account with the minimum permissions required for operational
monitoring.

## Installation

```bash
cd ~/srx-collector

python3 -m venv venv
source venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt

cp config.example.yaml config.yaml
nano config.yaml
```

## Configuration

Example:

```yaml
exporter:
  listen_address: 0.0.0.0
  listen_port: 9105
  collection_interval_seconds: 30

devices:
  - name: R3KL4W-vFW-01
    host: 192.168.68.98
    port: 830
    username: netconf
    password: CHANGE_ME

    interfaces:
      - ge-0/0/0
      - ge-0/0/1
      - fxp0
      - st0
```

Selecting a physical interface automatically includes its logical interfaces.
For example, selecting `ge-0/0/0` also includes `ge-0/0/0.0` and VLAN units.

Protect the live configuration:

```bash
chmod 600 config.yaml
```

Never commit `config.yaml` to source control.

## Test NETCONF access

The test utility reads the first device from `config.yaml`:

```bash
source venv/bin/activate
python test_netconf.py
```

## Run the command-line collector

```bash
source venv/bin/activate
python collector.py
```

This connects to each configured device and prints the collected values.

## Run the Prometheus exporter

```bash
source venv/bin/activate
python exporter.py
```

Default endpoint:

```text
http://0.0.0.0:9105/metrics
```

Verify locally:

```bash
curl -s http://localhost:9105/metrics | grep '^srx_'
```

## Prometheus scrape configuration

```yaml
scrape_configs:
  - job_name: juniper_netconf
    static_configs:
      - targets:
          - 127.0.0.1:9105
```

## Useful PromQL examples

CPU utilization:

```promql
100 - srx_route_engine_cpu_idle{device="192.168.68.98"}
```

Active sessions:

```promql
srx_sessions_active_sessions{device="192.168.68.98"}
```

Session utilization percentage:

```promql
100 *
srx_sessions_active_sessions{device="192.168.68.98"}
/
srx_sessions_max_sessions{device="192.168.68.98"}
```

Uptime in complete days:

```promql
floor(
  srx_route_engine_uptime_seconds{device="192.168.68.98"} / 86400
)
```

For a 300-day reboot policy, suggested thresholds are:

- green below 270 days;
- yellow from 270 days;
- red from 300 days.

Interface throughput in bits per second:

```promql
8 * rate(
  srx_interface_traffic_rx_bytes_total{
    device="192.168.68.98",
    interface="ge-0/0/0.0"
  }[1m]
)
```

Combined receive and transmit throughput:

```promql
8 * (
  rate(
    srx_interface_traffic_rx_bytes_total{
      device="192.168.68.98",
      interface="ge-0/0/0.0"
    }[1m]
  )
  +
  rate(
    srx_interface_traffic_tx_bytes_total{
      device="192.168.68.98",
      interface="ge-0/0/0.0"
    }[1m]
  )
)
```

MNHA role state:

```promql
srx_ha_role_state{device="192.168.68.98"}
```

Values:

- `2` = Active
- `1` = Backup or Standby
- `0` = Down or Unknown

Exporter health:

```promql
srx_exporter_up{device="192.168.68.98"}
```

## Grafana notes

For Canvas panels, use separate queries for values that need different units.
Grafana frequently names Prometheus result fields `Value`, so use distinct
legend names such as `Cpu98`, `Sessions98`, and `UptimeDays98`.

Recommended units:

- CPU: Percent (0-100)
- Sessions: None
- Uptime in days: None
- Byte rates converted with `8 * rate(...)`: bits per second
- Collection duration: seconds

## Documentation

- [Architecture](docs/architecture.md)
- [Adding collectors](docs/adding_collectors.md)
- [Metric reference](docs/metrics.md)
- [Troubleshooting](docs/troubleshooting.md)
- [systemd service](docs/systemd-service.md)
- [AI assistant context](AI_HELP.md)

## Security

See [SECURITY.md](SECURITY.md).

## License

No license has been selected yet. Add a `LICENSE` file before public
distribution.
