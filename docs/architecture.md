# Architecture

## Data flow

```text
Juniper SRX or vSRX
        |
        | NETCONF over SSH, normally TCP 830
        v
collectors/<feature>.py
        |
        | normalized Python dictionaries
        v
collector.py
        |
        | combined device metrics
        v
exporter.py
        |
        | cached latest successful result
        v
exporters/prometheus.py
        |
        | Prometheus exposition format
        v
/metrics on TCP 9105
```

## Responsibilities

### Collectors

A collector owns one Junos operational feature.

It executes an RPC, parses its XML response, and returns normalized values.
Collectors do not know about Prometheus queries or dashboards.

### `collector.py`

Imports and executes collectors for each configured device.

Device-specific selection, such as interface lists or Screen zones, is passed
from `config.yaml`.

### `exporter.py`

Runs collection cycles, retains the latest successful metrics, exposes
collection health, and serves the HTTP endpoint.

### `exporters/prometheus.py`

Converts normalized collector results to Prometheus metric families and
labels.

## Dynamic discovery

Object-based collectors should iterate over all entries returned by Junos.

The security policy collector is an example. It does not contain a configured
policy list. Every policy returned by
`get-security-policies-hit-count` becomes a labelled sample.

This design allows newly configured policies to appear without a Python code
change.

## Failure behaviour

A failed collection must be visible through exporter health metrics.

The exporter may retain the previous successful device values, but stale
values must not be confused with current collection health.
