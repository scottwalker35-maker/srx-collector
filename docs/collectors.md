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

## Collector documentation standard

Every collector module must document:

- the Junos operational command;
- the corresponding `display xml rpc` request;
- the repeating XML entry path, when applicable;
- whether values are counters, gauges, or states;
- whether returned objects are dynamically discovered;
- any configuration values passed to the collector.

Collectors must parse XML returned by NETCONF. They must not parse formatted
CLI tables.

- Added system_alarms collector: exports srx_system_alarm_active_count, srx_system_alarm_active, and srx_system_alarm_raised_timestamp_seconds from 'show system alarms' (get-system-alarm-information).

## IKE security associations

- Collector: `collectors/ike_security_associations.py`
- CLI: `show security ike security-associations`
- RPC: `<get-ike-security-associations-information/>`
- Discovery: every returned `ike-security-associations` entry.

## IKE security-association detail

Collector: `collectors/ike_security_associations_detail.py`

The summary RPC discovers every current IKE index. The detail collector then
runs `get-ike-security-associations-information` with `detail` and
`show-index-ike-security-association` for each index.

## IPsec security associations

Collector: `collectors/ipsec_security_associations.py`

RPC:

```xml
<get-security-associations-information/>
```

The collector dynamically discovers each returned tunnel index and records its
remote gateway, direction, SPI, algorithms, lifetime, and port.

## IPsec security-association detail

Collector: `collectors/ipsec_security_associations_detail.py`

The summary RPC discovers current tunnel indices. The detail RPC is then run
once for each index and returns tunnel-level and inbound/outbound SA data.
