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

## Primary objective

Modify the existing repository. Do not generate a replacement exporter.

The supplied repository context is authoritative.

Do not redesign the architecture. Extend the project by following the same
coding style, helper functions, naming conventions, collector return format,
Prometheus export patterns, and insertion points already present.

When an existing project pattern conflicts with a generic best practice,
preserve the existing project pattern unless the operator explicitly requests
a redesign.

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

## Core design principles

### Design principle 1: dynamically discover configured objects

When Junos returns a repeating list of configured objects, discover every
entry returned by the RPC.

Examples include:

- policies;
- interfaces;
- VPNs;
- routing instances;
- NAT rules;
- peers;
- zones.

Adding a configured object on the firewall should not require a Python code
change when the RPC already returns that object.

### Design principle 2: preserve repository architecture

Do not create a new application, framework, package layout, exporter library,
or configuration format.

Add the smallest change needed to support the new RPC.

### Design principle 3: one operational command must explain the collector

Every collector must document the Junos operational command, XML RPC, and
relevant XML response structure in its module docstring.

The collector should be understandable and testable from one Junos
operational command plus its `display xml` and `display xml rpc` output.

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
