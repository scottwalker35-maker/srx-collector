# Changelog

All notable changes to this project should be documented here.

## Unreleased

### Added

- Modular NETCONF collectors for system, MNHA, sessions, Routing Engine, and
  interfaces.
- Prometheus exporter health metrics.
- `srx_system_info` identity metric.
- `srx_ha_info` information metric.
- `srx_ha_role_state` numeric MNHA state.
- Routing Engine uptime in seconds.
- Physical and logical interface traffic, state, error, queue, and security
  flow statistics.
- Documentation for installation, architecture, metrics, troubleshooting,
  systemd, dashboards, and AI-assisted maintenance.
- Safe NETCONF test utility that reads `config.yaml`.

### Changed

- Expanded `config.example.yaml`.
- Removed hard-coded credentials from `test_netconf.py`.
- Documented Grafana Canvas unit and field-binding considerations.

### Security

- Added `.gitignore` rules for live configuration, virtual environments,
  generated caches, logs, and backups.
- Added guidance for protecting `config.yaml` and rotating exposed
  credentials.
