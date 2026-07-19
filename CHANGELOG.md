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

- Added system_alarms collector: exports srx_system_alarm_active_count, srx_system_alarm_active, and srx_system_alarm_raised_timestamp_seconds from 'show system alarms' (get-system-alarm-information).

## Unreleased

- Added the IKE security-association summary collector and metrics.

## Unreleased

- Added dynamic per-index IKE security-association detail collection.
- Added firewall-linked IKE lifetime, traffic, Phase 2, rekey, algorithm, and
  associated-tunnel metrics.

## Unreleased

- Added dynamic per-index IKE security-association detail collection.
- Added firewall-linked IKE lifetime, traffic, Phase 2, rekey, algorithm, and
  associated-tunnel metrics.

## Unreleased

- Added dynamic IPsec security-association summary collection.
- Added firewall-linked per-tunnel IPsec identity and lifetime metrics.

## Unreleased

- Added dynamic per-index IPsec security-association detail collection.
- Added firewall-linked tunnel, policy, identity, lifetime, replay, algorithm,
  event, and IKE-correlation metrics.
