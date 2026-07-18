# Adding a Collector

## 1. Obtain Junos XML

Run the operational command on the SRX and request XML output.

Example:

```text
show chassis routing-engine | display xml
```

Identify the Junos RPC and the XML element names.

## 2. Create the collector

Create:

```text
collectors/example.py
```

Template:

```python
"""
Collector: Example

CLI:
    show example

RPC:
    get-example-information
"""


def collect_example(client):
    root = client.rpc("get-example-information")

    return {
        "name": "example",
        "metrics": {
            "counter":
                root.findtext(".//counter"),
        },
    }
```

Use `lxml.etree` and direct dispatch when the RPC requires child elements.

## 3. Register the collector

In `collector.py`:

```python
from collectors.example import collect_example
```

Add it to:

```python
standard_collectors = (
    collect_system,
    collect_ha,
    collect_sessions,
    collect_route_engine,
    collect_example,
)
```

## 4. Test raw collection

```bash
source venv/bin/activate
python collector.py
```

Confirm the new section and values appear.

## 5. Verify Prometheus output

Numeric values normally export automatically:

```bash
curl -s http://localhost:9105/metrics |
grep '^srx_example_'
```

## 6. Handle strings only when needed

The generic exporter intentionally ignores nonnumeric strings.

When a string is useful as identity or state information, add a dedicated info
metric in `exporters/prometheus.py`.

Example:

```text
srx_example_info{state="READY"} 1
```

When Grafana thresholds or alerts need a numeric state, add an explicitly
documented mapping.

## 7. Validate

```bash
source venv/bin/activate
python -m compileall \
  collector.py \
  exporter.py \
  collectors \
  exporters \
  lib
```

## 8. Update documentation

Update:

- `README.md`
- `AI_HELP.md`
- `docs/metrics.md`
- `CHANGELOG.md`
