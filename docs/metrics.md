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

- Added system_alarms collector: exports srx_system_alarm_active_count, srx_system_alarm_active, and srx_system_alarm_raised_timestamp_seconds from 'show system alarms' (get-system-alarm-information).

## IKE security-association metrics

- `srx_ike_sa_total`
- `srx_ike_sa_up_total`
- `srx_ike_sa_down_total`
- `srx_ike_sa_up`
- `srx_ike_sa_info`

## Detailed IKE security-association metrics

Metrics use the `srx_ike_detail_` prefix. They include per-firewall discovery
and query totals, current SA state, remaining lifetime, packet and byte
counters, IPsec SA counts, Phase 2 counts, rekeys, associated tunnel counts,
and an information metric for negotiated algorithms and identities.

## IPsec security-association metrics

- `srx_ipsec_sa_total`
- `srx_ipsec_sa_present`
- `srx_ipsec_sa_remaining_lifetime_seconds`
- `srx_ipsec_sa_info`

Per-SA labels include `device`, `firewall`, `tunnel_index`, `remote_gateway`,
and `direction`.

## Detailed IPsec security-association metrics

Metrics use the `srx_ipsec_detail_` prefix. They include discovery and query
health, tunnel state and identity, negotiation statistics, event information,
and directional SA state, lifetimes, algorithms, SPI, replay settings, and IKE
index correlation.
