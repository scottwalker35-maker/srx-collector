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
