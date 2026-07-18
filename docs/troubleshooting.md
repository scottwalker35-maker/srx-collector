# Troubleshooting

## Exporter does not start

Run it interactively:

```bash
cd ~/srx-collector
source venv/bin/activate
python exporter.py
```

Check syntax:

```bash
python -m compileall \
  collector.py \
  exporter.py \
  collectors \
  exporters \
  lib
```

## Port 9105 already in use

```bash
sudo ss -tlnp | grep ':9105'
```

Stop the duplicate process or change `listen_port` in `config.yaml`.

## NETCONF connection failure

Verify TCP reachability:

```bash
nc -vz <srx-address> 830
```

Test the first configured device:

```bash
python test_netconf.py
```

On Junos, verify:

```text
show configuration system services netconf
show system connections | match 830
```

## No Prometheus metrics

```bash
curl -v http://localhost:9105/metrics
```

Check exporter logs and confirm a collection cycle completed successfully.

## Metric exists locally but not in Prometheus

Check the Prometheus target page and scrape configuration.

Example scrape target:

```yaml
- targets:
    - 127.0.0.1:9105
```

## String collector values are missing

The generic exporter only emits numeric values. String fields require a
dedicated info metric in `exporters/prometheus.py`.

## Interface not collected

Confirm the parent physical interface is listed under the device:

```yaml
interfaces:
  - ge-0/0/0
```

Selecting `ge-0/0/0` includes logical units such as `ge-0/0/0.0`.

## Uptime display is wrong in Grafana Canvas

The raw metric is seconds:

```promql
srx_route_engine_uptime_seconds{device="<device>"}
```

For whole days:

```promql
floor(
  srx_route_engine_uptime_seconds{device="<device>"} / 86400
)
```

Set the Grafana unit to `None`, not a duration unit.

Use a distinct legend such as:

```text
UptimeDays98
```

Canvas elements may otherwise bind to another generic field named `Value`.

## HA color remains healthy during an outage

The exporter retains the last good HA value. Include exporter health in the
query or alert.

Example active-state query that becomes zero when collection fails:

```promql
srx_ha_role_state{device="<device>"}
*
srx_exporter_up{device="<device>"}
```

Be aware that this maps a failed exporter to zero, which is also the defined
down or unknown HA state.
