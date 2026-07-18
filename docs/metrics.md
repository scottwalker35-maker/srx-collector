# Metric Reference

## Exporter health

### `srx_exporter_up`

Whether the most recent NETCONF collection succeeded.

- `1` = success
- `0` = failure

Labels:

- `device`

### `srx_exporter_collection_duration_seconds`

Duration of the latest collection attempt.

### `srx_exporter_last_success_timestamp_seconds`

Unix timestamp of the latest successful collection.

### `srx_exporter_collection_errors_total`

Number of collection failures since exporter startup.

## System information

### `srx_system_info`

Value is always `1`.

Labels:

- `device`
- `hostname`
- `model`
- `family`
- `junos_version`
- `serial_number`

## Multi-Node High Availability

### `srx_ha_info`

Value is always `1`.

Labels:

- `device`
- `node_status`
- `role`
- `peer_role`
- `health`
- `readiness`
- `peer_bfd`

### `srx_ha_role_state`

Numeric MNHA state:

- `2` = Active
- `1` = Backup or Standby
- `0` = Down or Unknown

A dashboard should also evaluate `srx_exporter_up`, because cached HA state is
retained when a collection fails.

## Sessions

Important metrics:

```text
srx_sessions_active_unicast_sessions
srx_sessions_active_multicast_sessions
srx_sessions_active_services_offload_sessions
srx_sessions_failed_sessions
srx_sessions_active_drop_sessions
srx_sessions_active_sessions
srx_sessions_active_session_valid
srx_sessions_active_session_pending
srx_sessions_active_session_invalidated
srx_sessions_active_session_other
srx_sessions_max_sessions
```

Session utilization:

```promql
100 *
srx_sessions_active_sessions{device="<device>"}
/
srx_sessions_max_sessions{device="<device>"}
```

## Routing Engine

Important metrics:

```text
srx_route_engine_memory_system_total_mb
srx_route_engine_memory_system_used_mb
srx_route_engine_memory_system_util
srx_route_engine_memory_control_plane_mb
srx_route_engine_memory_control_plane_used_mb
srx_route_engine_memory_control_plane_util
srx_route_engine_memory_data_plane_mb
srx_route_engine_memory_data_plane_used_mb
srx_route_engine_memory_data_plane_util
srx_route_engine_cpu_user
srx_route_engine_cpu_background
srx_route_engine_cpu_system
srx_route_engine_cpu_interrupt
srx_route_engine_cpu_idle
srx_route_engine_start_time_seconds
srx_route_engine_uptime_seconds
srx_route_engine_load_average_1
srx_route_engine_load_average_5
srx_route_engine_load_average_15
```

CPU utilization:

```promql
100 - srx_route_engine_cpu_idle{device="<device>"}
```

Uptime in completed days:

```promql
floor(
  srx_route_engine_uptime_seconds{device="<device>"} / 86400
)
```

Suggested 300-day policy thresholds:

- Base: green
- 270: yellow
- 300: red

## Interfaces

Labels:

- `device`
- `interface`

Common state metrics:

```text
srx_interface_admin_up
srx_interface_oper_up
```

Common traffic metrics:

```text
srx_interface_traffic_rx_bytes_total
srx_interface_traffic_tx_bytes_total
srx_interface_traffic_rx_packets_total
srx_interface_traffic_tx_packets_total
srx_interface_traffic_rx_bps
srx_interface_traffic_tx_bps
srx_interface_traffic_rx_pps
srx_interface_traffic_tx_pps
```

Cumulative byte counters should normally be graphed using `rate()`.

Receive bits per second:

```promql
8 * rate(
  srx_interface_traffic_rx_bytes_total{
    device="<device>",
    interface="<interface>"
  }[1m]
)
```

Transmit bits per second:

```promql
8 * rate(
  srx_interface_traffic_tx_bytes_total{
    device="<device>",
    interface="<interface>"
  }[1m]
)
```

Common physical error metrics include:

```text
srx_interface_errors_input_errors
srx_interface_errors_input_drops
srx_interface_errors_input_framing_errors
srx_interface_errors_input_runts
srx_interface_errors_input_giants
srx_interface_errors_output_errors
srx_interface_errors_output_drops
srx_interface_errors_output_collisions
srx_interface_errors_output_mtu_errors
```

Queue metric names include the queue number in the metric path because the
current generic flattener treats dictionary keys as name components.
