#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${1:-$HOME/srx-collector}"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$PROJECT_DIR/backups/documentation-$STAMP"

if [[ ! -d "$PROJECT_DIR" ]]; then
    echo "ERROR: Project directory not found: $PROJECT_DIR" >&2
    exit 1
fi

cd "$PROJECT_DIR"

required=(
    collector.py
    exporter.py
    exporters/prometheus.py
    collectors/security_screen.py
    collectors/security_policy_hit_count.py
)

for file in "${required[@]}"; do
    if [[ ! -f "$file" ]]; then
        echo "ERROR: Required project file is missing: $PROJECT_DIR/$file" >&2
        exit 1
    fi
done

mkdir -p "$BACKUP_DIR" docs scripts

backup_file() {
    local file="$1"

    if [[ -f "$file" ]]; then
        mkdir -p "$BACKUP_DIR/$(dirname "$file")"
        cp -a "$file" "$BACKUP_DIR/$file"
    fi
}

files_to_update=(
    README.md
    AI_HELP.md
    AI_COLLECTOR_INSTRUCTIONS.md
    CHANGELOG.md
    config.example.yaml
    docs/architecture.md
    docs/collectors.md
    docs/adding_collectors.md
    docs/metrics.md
    scripts/export_ai_collector_context.sh
    dashboards/README.md
)

for file in "${files_to_update[@]}"; do
    backup_file "$file"
done

cat > README.md <<'EOF'
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
EOF

cat > AI_COLLECTOR_INSTRUCTIONS.md <<'EOF'
# LLM Instructions: Add a Juniper SRX NETCONF Collector

Copy this entire file into ChatGPT, Claude, Gemini, Copilot, or another LLM.
After it, paste:

1. the output of `./scripts/export_ai_collector_context.sh`;
2. the Junos command output from `show ... | display xml`;
3. the Junos command output from `show ... | display xml rpc`;
4. the requested collector and metric name, when you have a preference.

The LLM must then generate one safe Bash installer script that modifies the
existing repository.

---

## Role

You are maintaining a Python project named **Juniper SRX NETCONF Prometheus
Exporter**.

Your task is to create a safe, repeatable Bash installation script that adds
one collector based on supplied Junos XML and RPC output.

Do not merely provide Python fragments. Produce one complete Bash script that
the operator can save, make executable, and run on the Ubuntu exporter host.

## Project architecture

### Collection path

```text
Junos operational command
    -> NETCONF RPC
    -> collectors/<feature>.py
    -> collector.py
    -> exporters/prometheus.py
    -> /metrics
```

### Collector contract

Every collector returns:

```python
{
    "name": "section_name",
    "metrics": {
        # normalized values
    },
}
```

The collector module:

- executes the NETCONF RPC;
- parses XML;
- normalizes the result into Python dictionaries;
- contains no Prometheus, Grafana, alerting, or dashboard logic.

### Registration

`collector.py` imports and executes every collector.

### Prometheus export

`exporters/prometheus.py` converts collector output into Prometheus samples.

Simple nested numeric dictionaries may use the generic exporter.

Dynamic object collections normally need a dedicated exporter method so that
stable object identity is represented with labels.

## Current collectors

- `collectors/system.py`
- `collectors/ha.py`
- `collectors/sessions.py`
- `collectors/route_engine.py`
- `collectors/interface_statistics.py`
- `collectors/security_screen.py`
- `collectors/security_policy_hit_count.py`

Use the supplied repository context as the source of truth. Never assume the
files still match an older example.

## Mandatory input

The operator will supply both:

```text
show <command> | display xml
```

and:

```text
show <command> | display xml rpc
```

Use the RPC output to build the request.

Use the XML output to build the parser.

Never parse the formatted CLI table.

If the XML or repository context is incomplete, stop and ask for the missing
content rather than guessing.

## Required design behaviour

### Automatic discovery

When Junos returns a repeating list of objects, discover every returned entry.

Examples include:

- security policies;
- interfaces;
- VPNs;
- routing instances;
- NAT rules;
- zones;
- peers;
- alarms.

Do not hardcode individual object names.

A new object added on the SRX must appear automatically on the next successful
collection cycle whenever the underlying RPC returns it.

### Stable labels

Use labels for stable identity fields such as:

- `device`
- `logical_system`
- `routing_instance`
- `from_zone`
- `to_zone`
- `zone`
- `policy`
- `interface`
- `vpn`
- `peer`
- `action`

Do not use an ordering index as the sole identity of an object when Junos can
renumber it after insertion, deletion, or reordering.

Avoid labels containing highly volatile or unbounded values such as:

- packet source addresses from arbitrary traffic;
- session IDs;
- timestamps;
- error text;
- complete descriptions that change frequently.

### Metric types

Use a metric name ending in `_total` for a cumulative counter.

Examples:

```text
srx_security_policy_hit_count_total
srx_screen_icmp_flood_total
```

Do not append `_total` to an instantaneous gauge.

The current exporter may internally use a generic sample helper. Preserve its
existing conventions rather than introducing a second Prometheus framework.

### Counter resets

Junos counters may reset after a reboot, failover, process restart, explicit
clear command, or configuration change. Export the raw counter and let
Prometheus functions such as `rate()` and `increase()` handle resets.

### Missing fields

Treat missing XML fields deliberately:

- optional identity string: use an empty string or documented default;
- optional numeric counter: normally use zero only when zero is semantically
  correct;
- unavailable measurement: omit it rather than inventing a value;
- malformed numeric text: do not crash the entire exporter.

### XML namespaces

Junos replies use XML namespaces.

Follow the XML handling pattern already present in the repository. When the
existing code normalizes namespaces or uses local-name-compatible parsing,
preserve that approach.

Do not assume an XPath works until it has been compared with the supplied XML.

## Installer script requirements

Produce one complete Bash script with:

```bash
#!/usr/bin/env bash
set -euo pipefail
```

Default project location:

```bash
PROJECT_DIR="${1:-$HOME/srx-collector}"
```

The script must:

1. verify that required project files exist;
2. create a timestamped backup directory inside:
   `backups/<collector-name>-YYYYMMDD-HHMMSS`;
3. back up every file it will modify;
4. define a rollback function;
5. use `trap` to restore the backup if installation fails;
6. create `collectors/<feature>.py`;
7. update `collector.py` idempotently;
8. update `exporters/prometheus.py` only when custom labels or formatting are
   required;
9. update relevant documentation:
   - `README.md`
   - `docs/collectors.md`
   - `docs/metrics.md`
   - `CHANGELOG.md`
   - this file's current collector list when appropriate;
10. never modify or display live passwords;
11. run Python syntax validation;
12. restart `srx-exporter`;
13. show service status;
14. wait for at least one collection cycle;
15. query `http://127.0.0.1:9105/metrics`;
16. display only the new metric family;
17. print useful verification commands;
18. leave a clear backup path in its output.

The script must be safe to run more than once.

Do not rewrite unrelated application files.

Do not use broad or fragile replacements when a more specific insertion
anchor is available.

When an expected insertion anchor is absent, fail and restore the backup.

## Python quality requirements

The collector must:

- include a module docstring showing the CLI command and RPC;
- have small parsing helpers where useful;
- use clear names;
- stay within reasonable line lengths;
- handle supported `ncclient` reply forms consistently with existing code;
- return deterministic dictionaries;
- avoid external dependencies not already in `requirements.txt`;
- avoid logging credentials or complete NETCONF connection objects.

## Exporter quality requirements

For a repeating object list, prefer one metric family with labels.

Example:

```text
srx_security_policy_hit_count_total{
  device="192.0.2.10",
  logical_system="root-logical-system",
  from_zone="trust",
  to_zone="untrust",
  policy="Internet",
  action="Permit"
} 650
```

Do not generate one new metric name per policy.

A dynamic policy list is good label cardinality because policy identity is
bounded by firewall configuration.

For a fixed set of Screen attack types, separate descriptive counter metric
names are acceptable:

```text
srx_screen_icmp_flood_total
srx_screen_tcp_syn_flood_total
```

Use the existing repository pattern as the deciding precedent.

## Validation requirements

At minimum, the generated installer must run:

```bash
python -m compileall -q \
    collector.py \
    collectors/<feature>.py \
    exporters/prometheus.py
```

After restart, it must verify:

```bash
sudo systemctl status srx-exporter --no-pager
```

and:

```bash
curl -fsS http://127.0.0.1:9105/metrics |
grep '^<new_metric_prefix>'
```

Also print:

```bash
sudo journalctl -u srx-exporter -n 100 --no-pager
```

as a troubleshooting command.

## Documentation output expected from the LLM

Before the script, briefly state:

- the proposed collector filename;
- the RPC being used;
- whether entries are fixed fields or dynamically discovered;
- the proposed metric family or families;
- the labels;
- whether each metric is a counter or gauge.

Then provide the complete installer script.

After the script, provide only:

- the command to run it;
- the expected metric example;
- one raw Prometheus verification command.

Do not include Grafana instructions unless explicitly requested.

## Security requirements

Never copy a password from supplied context into:

- source code;
- documentation;
- generated scripts;
- output examples;
- commit messages.

Use placeholders in all examples.

Do not expose sensitive values found in repository context.

## Decision checklist

Before generating the installer, verify:

- [ ] The RPC element and parameters are known.
- [ ] The repeating XML entry path is known, if applicable.
- [ ] Every proposed label comes from a stable XML field.
- [ ] Counter versus gauge semantics are understood.
- [ ] The metric name follows existing conventions.
- [ ] New objects will be discovered automatically.
- [ ] Repository insertion anchors were taken from current context.
- [ ] All modified files are backed up.
- [ ] Rollback is implemented.
- [ ] Syntax and endpoint validation are included.
- [ ] No dashboard-specific work was added.

If any required item is unknown, ask for clarification instead of inventing
the missing detail.
EOF

cat > docs/architecture.md <<'EOF'
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
EOF

cat > docs/collectors.md <<'EOF'
# Collectors

## System

File:

```text
collectors/system.py
```

Collects device identity and system information.

## High Availability

File:

```text
collectors/ha.py
```

Collects Juniper Multi-Node High Availability state.

## Sessions

File:

```text
collectors/sessions.py
```

Collects security flow session summary values.

## Routing Engine

File:

```text
collectors/route_engine.py
```

Collects Routing Engine CPU, memory, load, reboot, and uptime information.

## Interface statistics

File:

```text
collectors/interface_statistics.py
```

Collects configured physical interfaces and their logical units.

Configured parent interfaces are supplied through `config.yaml`.

## Security Screen statistics

File:

```text
collectors/security_screen.py
```

CLI:

```text
show security screen statistics zone <zone>
```

RPC:

```xml
<get-ids-statistics>
  <zone>untrust</zone>
</get-ids-statistics>
```

Zones are supplied through `security_screen_zones` in `config.yaml`.

The collector exports the fixed set of Screen counters returned by Junos for
each configured zone.

## Security policy hit counts

File:

```text
collectors/security_policy_hit_count.py
```

CLI:

```text
show security policies hit-count
```

RPC:

```xml
<get-security-policies-hit-count/>
```

Every policy returned by Junos is discovered automatically.

Policy names, source zones, destination zones, logical systems, and actions
are not hardcoded.

A newly configured policy appears on the next successful collection cycle.
EOF

cat > docs/metrics.md <<'EOF'
# Metrics

All device metrics include:

```text
device="<NETCONF host>"
```

## Exporter health

```text
srx_exporter_up
srx_exporter_collection_duration_seconds
srx_exporter_last_success_timestamp_seconds
srx_exporter_collection_errors_total
```

## Security Screen

Security Screen values are cumulative Junos counters.

Examples:

```text
srx_screen_icmp_flood_total{
  device="192.0.2.10",
  zone="untrust"
}
```

```text
srx_screen_tcp_syn_flood_total{
  device="192.0.2.10",
  zone="untrust"
}
```

```text
srx_screen_tcp_port_scan_total{
  device="192.0.2.10",
  zone="untrust"
}
```

Use Prometheus `increase()` or `rate()` to calculate activity over time.
Counter values may reset after a reboot, failover, clear command, or process
restart.

## Security policy hit counts

Metric:

```text
srx_security_policy_hit_count_total
```

Labels:

```text
device
logical_system
from_zone
to_zone
policy
action
```

Example:

```text
srx_security_policy_hit_count_total{
  device="192.0.2.10",
  logical_system="root-logical-system",
  from_zone="trust",
  to_zone="untrust",
  policy="Internet",
  action="Permit"
} 650
```

The Junos policy index is intentionally not exported as object identity.
Indexes can change when policy order changes.

The metric family is dynamically expandable: any policy returned by Junos
automatically becomes another labelled sample.

## Naming rules

Cumulative counters end in:

```text
_total
```

Instantaneous values and states do not use `_total`.

Stable configured object identity belongs in labels.

Unbounded traffic-derived identity, such as arbitrary source addresses or
session IDs, must not be used as labels.
EOF

cat > CHANGELOG.md <<'EOF'
# Changelog

## Unreleased

### Added

- LLM-specific collector implementation guide.
- Script for exporting sanitized repository context for an LLM.
- Documentation for collector architecture and metric conventions.

### Changed

- Repositioned the project as a general Juniper SRX NETCONF Prometheus
  exporter.
- Reduced dashboard-specific documentation from the exporter repository.
- Updated documentation for dynamically discovered objects.

## 2026-07-18

### Added

- Security Screen IDS collector.
- Security policy hit-count collector.
- Automatic policy discovery.
- Prometheus labels for policy logical system, zones, name, and action.
EOF

cat > scripts/export_ai_collector_context.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${1:-$HOME/srx-collector}"
OUTPUT_FILE="${2:-$PROJECT_DIR/ai-collector-context.txt}"

cd "$PROJECT_DIR"

files=(
    collector.py
    exporter.py
    exporters/prometheus.py
    lib/netconf.py
    collectors/security_screen.py
    collectors/security_policy_hit_count.py
    config.example.yaml
    README.md
    docs/collectors.md
    docs/metrics.md
)

: > "$OUTPUT_FILE"

{
    echo "# Juniper SRX Prometheus Exporter - LLM Context"
    echo
    echo "Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo
    echo "The live config.yaml file is deliberately excluded."
    echo "Review this output before pasting it into an LLM."
    echo
} >> "$OUTPUT_FILE"

for file in "${files[@]}"; do
    if [[ ! -f "$file" ]]; then
        continue
    fi

    {
        echo
        echo "================================================================"
        echo "FILE: $file"
        echo "================================================================"
        sed -E \
            -e 's/(password:[[:space:]]*).*/\1REDACTED/I' \
            -e 's/(password[[:space:]]*=[[:space:]]*)[^,)]*/\1"REDACTED"/I' \
            "$file"
    } >> "$OUTPUT_FILE"
done

chmod 600 "$OUTPUT_FILE"

echo "Created: $OUTPUT_FILE"
echo
echo "Review it before sharing:"
echo "  less \"$OUTPUT_FILE\""
echo
echo "Then paste these items into the LLM in order:"
echo "  1. AI_COLLECTOR_INSTRUCTIONS.md"
echo "  2. $OUTPUT_FILE"
echo "  3. Junos '| display xml' output"
echo "  4. Junos '| display xml rpc' output"
EOF

chmod +x scripts/export_ai_collector_context.sh

# AI_HELP.md was the older general-purpose file. Preserve it in the backup,
# then replace it with a pointer so there is only one authoritative LLM guide.
cat > AI_HELP.md <<'EOF'
# AI Assistance

The authoritative LLM guide for adding a Juniper SRX collector is:

```text
AI_COLLECTOR_INSTRUCTIONS.md
```

Generate current, sanitized repository context with:

```bash
./scripts/export_ai_collector_context.sh
```
EOF

# Keep existing dashboard assets, but remove the old dashboard-specific README
# from the project documentation scope.
if [[ -f dashboards/README.md ]]; then
    rm -f dashboards/README.md
fi

if [[ -d dashboards ]] && [[ -z "$(find dashboards -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
    rmdir dashboards
fi

# Ensure config.example.yaml documents Security Screen zones without touching
# the live config.yaml.
if [[ -f config.example.yaml ]]; then
    PYTHON="$PROJECT_DIR/venv/bin/python"
    [[ -x "$PYTHON" ]] || PYTHON="$(command -v python3)"

    "$PYTHON" - <<'PYEOF'
from pathlib import Path
import yaml

path = Path("config.example.yaml")

with path.open("r", encoding="utf-8") as handle:
    config = yaml.safe_load(handle) or {}

devices = config.get("devices", [])

if isinstance(devices, list):
    for device in devices:
        if not isinstance(device, dict):
            continue

        zones = device.get("security_screen_zones")

        if zones is None:
            device["security_screen_zones"] = ["untrust"]
        elif isinstance(zones, list) and "untrust" not in zones:
            zones.append("untrust")

with path.open("w", encoding="utf-8") as handle:
    yaml.safe_dump(
        config,
        handle,
        sort_keys=False,
        default_flow_style=False,
    )
PYEOF
fi

echo
echo "Validating Python..."

PYTHON="$PROJECT_DIR/venv/bin/python"
[[ -x "$PYTHON" ]] || PYTHON="$(command -v python3)"

"$PYTHON" -m compileall -q \
    collector.py \
    exporter.py \
    collectors \
    exporters \
    lib

if [[ -f config.example.yaml ]]; then
    echo "Validating config.example.yaml..."

    "$PYTHON" - <<'PYEOF'
import yaml

with open("config.example.yaml", "r", encoding="utf-8") as handle:
    yaml.safe_load(handle)

print("config.example.yaml is valid YAML")
PYEOF
fi

echo
echo "Creating sanitized LLM context..."
./scripts/export_ai_collector_context.sh

echo
echo "Documentation update complete."
echo "Backup: $BACKUP_DIR"
echo
echo "Review changes:"
echo "  cd \"$PROJECT_DIR\""
echo "  git status"
echo "  git diff -- README.md AI_HELP.md AI_COLLECTOR_INSTRUCTIONS.md \\"
echo "    CHANGELOG.md config.example.yaml docs scripts"
echo
echo "Suggested commit:"
echo '  git add README.md AI_HELP.md AI_COLLECTOR_INSTRUCTIONS.md \'
echo '    CHANGELOG.md config.example.yaml docs scripts dashboards/README.md'
echo '  git commit -m "Document dynamic collectors and LLM collector workflow"'
