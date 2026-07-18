# AI Assistant Context

Copy this file into ChatGPT, Claude, Gemini, Copilot, or another AI assistant
before asking for help with this repository.

---

You are assisting with a Python project named **Juniper SRX NETCONF Prometheus
Exporter**.

## Project purpose

The project connects to Juniper SRX and vSRX firewalls with NETCONF, executes
Junos operational RPCs, stores the latest results in memory, and exposes them
as Prometheus metrics for Grafana.

The project is intended to replace or supplement older SNMP and Cacti
monitoring with faster, richer NETCONF-based collection.

## Architecture

### `collector.py`

Responsibilities:

- load `config.yaml`;
- instantiate and execute every collector;
- combine collector results into one nested dictionary;
- provide a command-line mode that prints collected metrics.

Collector registration currently occurs in `collect_device_metrics()`.

### `exporter.py`

Responsibilities:

- load configuration;
- connect to each SRX on every collection cycle;
- call `collect_device_metrics()`;
- update the Prometheus metric cache;
- record exporter health, collection time, last success, and errors;
- run the HTTP metrics endpoint.

### `collectors/`

Each collector owns one Junos feature.

Current collectors:

- `system.py`
- `ha.py`
- `sessions.py`
- `route_engine.py`
- `interface_statistics.py`

Every collector must return:

```python
{
    "name": "section_name",
    "metrics": {
        "metric_name": value,
    },
}
```

Collectors should return raw Junos values with minimal interpretation.

### `exporters/prometheus.py`

Responsibilities:

- convert numeric collector values into Prometheus gauges;
- recursively flatten nested numeric dictionaries;
- add the `device` label;
- add `interface` labels for interface metrics;
- expose string information through dedicated info metrics;
- preserve metric names and label compatibility.

Special string exporters currently exist for:

- `srx_system_info`
- `srx_ha_info`

MNHA role is also exported numerically as:

```text
srx_ha_role_state
```

Values:

- 2 = ACTIVE
- 1 = BACKUP or STANDBY
- 0 = DOWN, OFFLINE, FAILED, or UNKNOWN

### `lib/netconf.py`

Responsibilities:

- establish and close NETCONF sessions;
- execute simple Junos RPCs;
- normalize ncclient XML reply handling.

## Coding rules

When proposing changes:

1. Preserve existing metric names unless the user explicitly requests a
   breaking change.
2. Keep collectors independent of Prometheus and Grafana.
3. Put Prometheus formatting and label logic in
   `exporters/prometheus.py`.
4. Use Junos RPCs rather than screen-scraping CLI output.
5. Never hard-code device IP addresses, usernames, passwords, interface
   names, or site-specific values in Python.
6. Keep configuration in YAML.
7. Add clear docstrings.
8. Handle missing XML fields without crashing where practical.
9. Missing state must not automatically be interpreted as down unless that
   behavior is explicitly intended.
10. Retain the last good metrics when a collection fails, but use
    `srx_exporter_up` to indicate current collection health.
11. Update documentation when adding a collector or metric.
12. Provide complete replacement files or safe patch scripts rather than
    vague partial snippets when the user requests implementation help.
13. Back up files before modifying them.
14. Validate Python syntax after changes with `python -m compileall`.
15. Do not expose or repeat passwords found in logs or uploaded files.

## Existing conventions

Generic non-interface metric:

```text
srx_<collector_name>_<metric_path>
```

Interface metric:

```text
srx_interface_<metric_path>{device="...",interface="..."}
```

Information metric:

```text
srx_<feature>_info{label1="...",label2="..."} 1
```

Exporter metrics:

```text
srx_exporter_up
srx_exporter_collection_duration_seconds
srx_exporter_last_success_timestamp_seconds
srx_exporter_collection_errors_total
```

## Current important metrics

```text
srx_system_info
srx_ha_info
srx_ha_role_state
srx_sessions_active_sessions
srx_sessions_max_sessions
srx_route_engine_cpu_idle
srx_route_engine_uptime_seconds
srx_interface_traffic_rx_bytes_total
srx_interface_traffic_tx_bytes_total
srx_interface_oper_up
srx_interface_admin_up
```

## Useful PromQL

CPU utilization:

```promql
100 - srx_route_engine_cpu_idle{device="<device>"}
```

Uptime in whole days:

```promql
floor(
  srx_route_engine_uptime_seconds{device="<device>"} / 86400
)
```

Session utilization:

```promql
100 *
srx_sessions_active_sessions{device="<device>"}
/
srx_sessions_max_sessions{device="<device>"}
```

Interface receive throughput:

```promql
8 * rate(
  srx_interface_traffic_rx_bytes_total{
    device="<device>",
    interface="<interface>"
  }[1m]
)
```

MNHA state:

```promql
srx_ha_role_state{device="<device>"}
```

## Adding a collector

1. Create `collectors/<feature>.py`.
2. Implement `collect_<feature>(client)`.
3. Return the standard collector dictionary.
4. Import and register it in `collector.py`.
5. Verify raw collection with `python collector.py`.
6. Numeric values should export automatically.
7. Add a dedicated exporter method only when strings must become labels or
   when custom numeric state mapping is required.
8. Update `docs/metrics.md`, `README.md`, and this file.
9. Restart the exporter.
10. Verify with `curl http://localhost:9105/metrics`.

## Questions the AI should ask before making uncertain changes

- Which Junos release and SRX platform are being used?
- What is the exact CLI output and corresponding XML RPC output?
- Is the requested state MNHA, chassis cluster, or another HA technology?
- Must existing dashboards keep working with current metric names?
- Should a missing value be omitted, mapped to zero, or exposed as unknown?
- Which physical interfaces should be collected?

## Expected answer style

- Be direct and operational.
- Do not guess about file contents that have not been provided.
- Use complete commands.
- Explain where each command is run.
- Separate Linux shell, Junos CLI, PromQL, and Grafana instructions.
- Avoid destructive commands unless they are necessary and clearly marked.
