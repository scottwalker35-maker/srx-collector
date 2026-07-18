# Architecture

## Data flow

```text
config.yaml
    |
    v
exporter.py
    |
    v
NetconfClient
    |
    v
collect_device_metrics()
    |
    +-- system
    +-- MNHA
    +-- sessions
    +-- Routing Engine
    +-- interfaces
    |
    v
in-memory latest-value cache
    |
    v
Prometheus /metrics endpoint
    |
    v
Prometheus
    |
    v
Grafana
```

## Collector contract

Every collector returns:

```python
{
    "name": "feature_name",
    "metrics": {
        "key": value,
    },
}
```

Collectors should focus on:

- dispatching the Junos RPC;
- parsing XML;
- returning raw or minimally normalized values;
- representing missing data safely.

Collectors should not:

- know about Prometheus names;
- know about Grafana;
- add site-specific labels;
- contain credentials;
- hard-code device addresses.

## Prometheus translation

Numeric values are recursively flattened.

Example collector result:

```python
{
    "name": "example",
    "metrics": {
        "traffic": {
            "rx_bytes_total": 123,
        },
    },
}
```

becomes:

```text
srx_example_traffic_rx_bytes_total{device="..."} 123
```

Interface values receive both `device` and `interface` labels.

String values are ignored by the generic numeric exporter. Features requiring
string data must use a dedicated information metric, such as:

```text
srx_system_info{hostname="...",model="..."} 1
```

## Error behavior

When collection succeeds:

- metrics are replaced with the latest result;
- `srx_exporter_up` becomes `1`;
- last success time is updated.

When collection fails:

- the last good feature metrics are retained;
- `srx_exporter_up` becomes `0`;
- the collection error counter increases.

Dashboards and alerts should always check `srx_exporter_up` rather than
assuming cached feature metrics represent current device health.

## Device identity

The configured management address is used as the stable `device` label. This
value is available even when system information cannot be collected.

## Threading model

One background thread performs sequential collection for configured devices.
The Prometheus HTTP server reads a thread-safe snapshot of the most recent
results.
