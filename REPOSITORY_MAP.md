# Repository Map

This file gives an LLM enough architectural context to add a normal collector
without requiring the complete repository source on every request.

The existing repository is authoritative. Do not redesign it.

## Main files

### `collector.py`

Primary collector orchestration.

Typical responsibilities:

- load enabled collector names from configuration;
- import or register collector modules;
- call collectors using the existing NETCONF connection;
- combine returned metric samples;
- handle collector failures using the existing logging pattern.

A new collector may require a small registration or import change here. Follow
the exact pattern used by existing collectors.

### `exporter.py`

Application entry point and exporter service orchestration.

A normal collector should not require changes here unless the repository's
existing pattern explicitly requires registration in this file.

Do not redesign the service, threading model, polling loop, or configuration
loading.

### `exporters/prometheus.py`

Prometheus rendering and HTTP exposition.

Collectors should return data in the same structure as existing collectors.

Do not add collector-specific rendering logic unless the existing repository
architecture requires it.

### `lib/netconf.py`

Shared NETCONF connection and RPC helpers.

Use these helpers rather than creating a second NETCONF client.

Do not run CLI commands through SSH and do not scrape formatted CLI output.

### `config.example.yaml`

Update this only when the collector requires a new option or must be listed
among selectable collectors.

Never include real credentials or secrets.

## Collector directory

### `collectors/`

One Python module per collector.

Existing collectors are the coding templates.

A new collector must:

- use NETCONF RPC;
- parse XML;
- use the repository's existing namespace-normalization approach;
- dynamically discover repeating Junos objects;
- avoid hardcoded policy, interface, zone, peer, VPN, NAT rule, or routing
  instance names;
- return metrics using the same project structures and naming conventions;
- handle missing XML elements safely;
- avoid unstable or high-cardinality labels.

Every new collector module must document:

1. Junos operational command;
2. relevant XML response structure;
3. `show ... | display xml rpc`;
4. repeating XML entry path;
5. metric names and types;
6. dynamic discovery behavior.

## Documentation

Update the relevant documentation whenever a collector is added:

- `README.md` when supported features or overview changes;
- `COLLECTORS.md` or `docs/collectors.md`;
- `CHANGELOG.md`;
- `docs/metrics.md` when present;
- `config.example.yaml` when configuration changes.

## Optional source context

### `scripts/export_ai_collector_context.sh`

This helper is optional.

Do not require its output for a normal collector request.

Use it only when a specific implementation detail cannot be determined from:

- `AI_COLLECTOR_INSTRUCTIONS.md`;
- this repository map;
- supplied Junos XML;
- supplied Junos XML RPC.

Ask for the smallest missing source file first. Request the full generated
repository context only as a last resort.

## Installer scripts

When requested, generate one idempotent Bash installer that:

- creates timestamped backups;
- makes the smallest required source changes;
- validates Python and YAML;
- restarts only the relevant service;
- verifies service health and metrics;
- prints rollback instructions;
- does not expose credentials.
