import math
import re
import threading
import time
from numbers import Number

from prometheus_client.core import GaugeMetricFamily


_METRIC_NAME_PATTERN = re.compile(r"[^a-zA-Z0-9_:]")


def _sanitize_metric_name(value):
    """
    Convert a collector key into a valid Prometheus metric-name component.
    """

    value = str(value).strip().lower()
    value = _METRIC_NAME_PATTERN.sub("_", value)
    value = re.sub(r"_+", "_", value)
    return value.strip("_")


def _numeric_value(value):
    """
    Convert supported values to a finite float.

    Strings such as timestamps, interface states, versions and descriptions
    are intentionally ignored by the generic numeric exporter.

    Collectors requiring string labels, such as system information, are
    handled separately.
    """

    if value is None or isinstance(value, bool):
        return None

    if isinstance(value, Number):
        number = float(value)

    elif isinstance(value, str):
        value = value.strip()

        if not value:
            return None

        try:
            number = float(value)
        except ValueError:
            return None

    else:
        return None

    if not math.isfinite(number):
        return None

    return number


def _label_value(value):
    """
    Convert a collector value into a safe Prometheus label value.
    """

    if value is None:
        return ""

    return str(value).strip()


def _flatten_numeric_metrics(value, path=()):
    """
    Recursively flatten numeric values from nested collector dictionaries.

    Example:

        {
            "traffic": {
                "rx_bytes_total": 123
            }
        }

    becomes:

        (("traffic", "rx_bytes_total"), 123)
    """

    if isinstance(value, dict):
        for key, child_value in value.items():
            yield from _flatten_numeric_metrics(
                child_value,
                path + (_sanitize_metric_name(key),),
            )

        return

    number = _numeric_value(value)

    if number is not None:
        yield path, number


class SrxPrometheusCollector:
    """
    Thread-safe Prometheus collector backed by the latest NETCONF results.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._devices = {}

    def update_device(
        self,
        device_name,
        metrics,
        duration_seconds,
        collected_at=None,
    ):
        """
        Store a successful collection for one SRX device.
        """

        if collected_at is None:
            collected_at = time.time()

        with self._lock:
            previous = self._devices.get(device_name, {})

            self._devices[device_name] = {
                "metrics": metrics,
                "up": 1,
                "duration_seconds": float(duration_seconds),
                "last_success_timestamp_seconds": float(collected_at),
                "collection_errors_total": previous.get(
                    "collection_errors_total",
                    0,
                ),
            }

    def mark_device_error(self, device_name, duration_seconds):
        """
        Record a failed collection while retaining the last good metrics.
        """

        with self._lock:
            previous = self._devices.get(device_name, {})

            self._devices[device_name] = {
                "metrics": previous.get("metrics", {}),
                "up": 0,
                "duration_seconds": float(duration_seconds),
                "last_success_timestamp_seconds": previous.get(
                    "last_success_timestamp_seconds",
                    0,
                ),
                "collection_errors_total": previous.get(
                    "collection_errors_total",
                    0,
                ) + 1,
            }

    def _snapshot(self):
        """
        Return a shallow snapshot safe for Prometheus collection.
        """

        with self._lock:
            return {
                device_name: {
                    "metrics": values.get("metrics", {}),
                    "up": values.get("up", 0),
                    "duration_seconds": values.get(
                        "duration_seconds",
                        0,
                    ),
                    "last_success_timestamp_seconds": values.get(
                        "last_success_timestamp_seconds",
                        0,
                    ),
                    "collection_errors_total": values.get(
                        "collection_errors_total",
                        0,
                    ),
                }
                for device_name, values in self._devices.items()
            }

    def collect(self):
        """
        Yield Prometheus metric families.
        """

        snapshot = self._snapshot()

        exporter_up = GaugeMetricFamily(
            "srx_exporter_up",
            "Whether the most recent NETCONF collection succeeded.",
            labels=["device"],
        )

        collection_duration = GaugeMetricFamily(
            "srx_exporter_collection_duration_seconds",
            "Duration of the most recent NETCONF collection.",
            labels=["device"],
        )

        last_success = GaugeMetricFamily(
            "srx_exporter_last_success_timestamp_seconds",
            "Unix timestamp of the most recent successful collection.",
            labels=["device"],
        )

        collection_errors = GaugeMetricFamily(
            "srx_exporter_collection_errors_total",
            "Total NETCONF collection failures since exporter startup.",
            labels=["device"],
        )

        for device_name, device_data in snapshot.items():
            labels = [device_name]

            exporter_up.add_metric(
                labels,
                device_data["up"],
            )

            collection_duration.add_metric(
                labels,
                device_data["duration_seconds"],
            )

            last_success.add_metric(
                labels,
                device_data["last_success_timestamp_seconds"],
            )

            collection_errors.add_metric(
                labels,
                device_data["collection_errors_total"],
            )

        yield exporter_up
        yield collection_duration
        yield last_success
        yield collection_errors

        metric_samples = {}

        for device_name, device_data in snapshot.items():
            metrics = device_data["metrics"]

            for section_name, section_values in metrics.items():

                if section_name == "system":
                    self._collect_system_info(
                        metric_samples=metric_samples,
                        device_name=device_name,
                        system_values=section_values,
                    )
                    continue

                if section_name == "ha":
                    self._collect_ha_info(
                        metric_samples=metric_samples,
                        device_name=device_name,
                        ha_values=section_values,
                    )
                    continue

                if section_name == "system_alarms":
                    self._collect_system_alarms_samples(
                        metric_samples=metric_samples,
                        device_name=device_name,
                        alarms_section=section_values,
                    )
                    continue

                if section_name == "security_policy_hit_count":
                    self._collect_security_policy_hit_count_samples(
                        metric_samples=metric_samples,
                        device_name=device_name,
                        policies=section_values,
                    )
                    continue

                if section_name == "security_screen":
                    self._collect_security_screen_samples(
                        metric_samples=metric_samples,
                        device_name=device_name,
                        zones=section_values,
                    )
                    continue

                if section_name == "interface_statistics":
                    self._collect_interface_samples(
                        metric_samples=metric_samples,
                        device_name=device_name,
                        interfaces=section_values,
                    )
                    continue

                if section_name == "ipsec_security_associations_detail":
                    self._collect_ipsec_security_association_detail_samples(
                        metric_samples=metric_samples,
                        device_name=device_name,
                        firewall_name=_label_value(
                            metrics.get("system", {}).get("hostname")
                        ),
                        ipsec_values=section_values,
                    )
                    continue

                if section_name == "ipsec_security_associations":
                    self._collect_ipsec_security_association_samples(
                        metric_samples=metric_samples,
                        device_name=device_name,
                        firewall_name=_label_value(
                            metrics.get("system", {}).get("hostname")
                        ),
                        ipsec_values=section_values,
                    )
                    continue

                if section_name == "ike_security_associations_detail":
                    self._collect_ike_security_association_detail_samples(
                        metric_samples=metric_samples,
                        device_name=device_name,
                        firewall_name=_label_value(
                            metrics.get("system", {}).get("hostname")
                        ),
                        ike_values=section_values,
                    )
                    continue

                if section_name == "ike_security_associations":
                    self._collect_ike_security_association_samples(
                        metric_samples=metric_samples,
                        device_name=device_name,
                        firewall_name=_label_value(
                            metrics.get("system", {}).get("hostname")
                        ),
                        ike_values=section_values,
                    )
                    continue

                self._collect_section_samples(
                    metric_samples=metric_samples,
                    device_name=device_name,
                    section_name=section_name,
                    section_values=section_values,
                )

        for metric_name in sorted(metric_samples):
            metric_data = metric_samples[metric_name]

            family = GaugeMetricFamily(
                metric_name,
                metric_data["description"],
                labels=metric_data["label_names"],
            )

            for sample in metric_data["samples"]:
                family.add_metric(
                    sample["label_values"],
                    sample["value"],
                )

            yield family

    def _collect_ipsec_security_association_detail_samples(
        self,
        metric_samples,
        device_name,
        firewall_name,
        ipsec_values,
    ):
        """Export detailed data for every dynamically discovered IPsec tunnel."""

        summary_metrics = {
            "srx_ipsec_detail_discovered_total": (
                "Number of IPsec tunnel indices discovered by the summary RPC.",
                ipsec_values.get("discovered_total"),
            ),
            "srx_ipsec_detail_collected_total": (
                "Number of IPsec tunnel detail records collected successfully.",
                ipsec_values.get("collected_total"),
            ),
            "srx_ipsec_detail_query_failures_total": (
                "Number of per-index IPsec detail RPC failures in the latest cycle.",
                ipsec_values.get("query_failures_total"),
            ),
        }

        for metric_name, (description, raw_value) in summary_metrics.items():
            number = _numeric_value(raw_value)
            if number is None:
                continue
            if metric_name not in metric_samples:
                metric_samples[metric_name] = {
                    "description": description,
                    "label_names": ["device", "firewall"],
                    "samples": [],
                }
            metric_samples[metric_name]["samples"].append({
                "label_values": [device_name, firewall_name],
                "value": number,
            })

        tunnels = ipsec_values.get("tunnels", {})
        tunnel_label_names = [
            "device",
            "firewall",
            "tunnel_index",
            "vpn",
            "remote_gateway",
            "bind_interface",
            "logical_system",
        ]

        tunnel_numeric_metrics = {
            "srx_ipsec_detail_up": ("Whether the IPsec tunnel block is up.", "up"),
            "srx_ipsec_detail_negotiations_total": ("IPsec negotiations recorded for the tunnel.", "negotiations_total"),
            "srx_ipsec_detail_negotiation_failures_total": ("Failed IPsec negotiations recorded for the tunnel.", "negotiation_failures_total"),
            "srx_ipsec_detail_deletions_total": ("IPsec deletions recorded for the tunnel.", "deletions_total"),
            "srx_ipsec_detail_event_count": ("Number of event records returned for the tunnel.", "event_count"),
            "srx_ipsec_detail_last_event_repeat_count": ("Repeat count for the newest returned tunnel event.", "last_event_repeat_count"),
        }

        direction_numeric_metrics = {
            "srx_ipsec_detail_sa_installed": ("Whether the directional IPsec SA is installed.", "installed"),
            "srx_ipsec_detail_sa_hard_lifetime_seconds": ("Remaining hard lifetime for the directional SA.", "hard_lifetime_seconds"),
            "srx_ipsec_detail_sa_soft_lifetime_seconds": ("Remaining soft lifetime for the directional SA.", "soft_lifetime_seconds"),
            "srx_ipsec_detail_sa_replay_window_size": ("Replay-window size for the directional SA.", "replay_window_size"),
        }

        for tunnel_index in sorted(
            tunnels,
            key=lambda value: int(value) if str(value).isdigit() else str(value),
        ):
            tunnel = tunnels[tunnel_index]
            tunnel_labels = [
                device_name,
                firewall_name,
                _label_value(tunnel.get("tunnel_index")),
                _label_value(tunnel.get("vpn_name")),
                _label_value(tunnel.get("remote_gateway")),
                _label_value(tunnel.get("bind_interface")),
                _label_value(tunnel.get("logical_system")),
            ]

            for metric_name, (description, field_name) in tunnel_numeric_metrics.items():
                number = _numeric_value(tunnel.get(field_name))
                if number is None:
                    continue
                if metric_name not in metric_samples:
                    metric_samples[metric_name] = {
                        "description": description,
                        "label_names": tunnel_label_names,
                        "samples": [],
                    }
                metric_samples[metric_name]["samples"].append({
                    "label_values": tunnel_labels,
                    "value": number,
                })

            info_name = "srx_ipsec_detail_info"
            if info_name not in metric_samples:
                metric_samples[info_name] = {
                    "description": "Detailed IPsec tunnel identity, policy, and negotiated settings.",
                    "label_names": tunnel_label_names + [
                        "state", "local_gateway", "local_identity", "remote_identity",
                        "traffic_selector_type", "ike_version", "pfs_group",
                        "policy", "quantum_secured", "df_bit", "copy_outer_dscp",
                        "passive_mode_tunneling", "distribution_key",
                        "last_event_time", "last_event_description",
                    ],
                    "samples": [],
                }
            metric_samples[info_name]["samples"].append({
                "label_values": tunnel_labels + [
                    _label_value(tunnel.get("block_state")),
                    _label_value(tunnel.get("local_gateway")),
                    _label_value(tunnel.get("local_identity")),
                    _label_value(tunnel.get("remote_identity")),
                    _label_value(tunnel.get("traffic_selector_type")),
                    _label_value(tunnel.get("ike_version")),
                    _label_value(tunnel.get("pfs_group")),
                    _label_value(tunnel.get("policy_name")),
                    _label_value(tunnel.get("quantum_secured")),
                    _label_value(tunnel.get("df_bit")),
                    _label_value(tunnel.get("copy_outer_dscp")),
                    _label_value(tunnel.get("passive_mode_tunneling")),
                    _label_value(tunnel.get("distribution_key")),
                    _label_value(tunnel.get("last_event_time")),
                    _label_value(tunnel.get("last_event_description")),
                ],
                "value": 1,
            })

            for direction, sa in tunnel.get("directions", {}).items():
                direction_label_names = tunnel_label_names + [
                    "direction", "spi", "ike_index", "protocol",
                ]
                direction_labels = tunnel_labels + [
                    _label_value(direction),
                    _label_value(sa.get("spi")),
                    _label_value(sa.get("ike_index")),
                    _label_value(sa.get("protocol")),
                ]

                for metric_name, (description, field_name) in direction_numeric_metrics.items():
                    number = _numeric_value(sa.get(field_name))
                    if number is None:
                        continue
                    if metric_name not in metric_samples:
                        metric_samples[metric_name] = {
                            "description": description,
                            "label_names": direction_label_names,
                            "samples": [],
                        }
                    metric_samples[metric_name]["samples"].append({
                        "label_values": direction_labels,
                        "value": number,
                    })

                sa_info_name = "srx_ipsec_detail_sa_info"
                if sa_info_name not in metric_samples:
                    metric_samples[sa_info_name] = {
                        "description": "Directional IPsec SA algorithms, replay settings, and state.",
                        "label_names": direction_label_names + [
                            "state", "encryption_algorithm", "authentication_algorithm",
                            "hmac_algorithm", "esp_encryption_algorithm", "mode", "type",
                            "anti_replay_service", "extended_sequence_number",
                            "tunnel_establishment", "monitoring_state", "lifesize_remaining",
                        ],
                        "samples": [],
                    }
                metric_samples[sa_info_name]["samples"].append({
                    "label_values": direction_labels + [
                        _label_value(sa.get("state")),
                        _label_value(sa.get("encryption_algorithm")),
                        _label_value(sa.get("authentication_algorithm")),
                        _label_value(sa.get("hmac_algorithm")),
                        _label_value(sa.get("esp_encryption_algorithm")),
                        _label_value(sa.get("mode")),
                        _label_value(sa.get("type")),
                        _label_value(sa.get("anti_replay_service")),
                        _label_value(sa.get("extended_sequence_number")),
                        _label_value(sa.get("tunnel_establishment")),
                        _label_value(sa.get("monitoring_state")),
                        _label_value(sa.get("lifesize_remaining")),
                    ],
                    "value": 1,
                })

    def _collect_ipsec_security_association_samples(
        self,
        metric_samples,
        device_name,
        firewall_name,
        ipsec_values,
    ):
        """Export dynamically discovered IPsec security associations."""

        total_value = _numeric_value(ipsec_values.get("sa_total"))

        if total_value is not None:
            metric_name = "srx_ipsec_sa_total"
            metric_samples.setdefault(
                metric_name,
                {
                    "description": (
                        "Number of IPsec security associations currently "
                        "returned by the firewall."
                    ),
                    "label_names": ["device", "firewall"],
                    "samples": [],
                },
            )
            metric_samples[metric_name]["samples"].append(
                {
                    "label_values": [device_name, firewall_name],
                    "value": total_value,
                }
            )

        associations = ipsec_values.get("associations", {})
        base_label_names = [
            "device",
            "firewall",
            "tunnel_index",
            "remote_gateway",
            "direction",
        ]

        numeric_metrics = {
            "srx_ipsec_sa_present": (
                "Whether the IPsec SA entry is currently present.",
                "present",
            ),
            "srx_ipsec_sa_remaining_lifetime_seconds": (
                "Remaining IPsec SA lifetime in seconds.",
                "remaining_lifetime_seconds",
            ),
        }

        for tunnel_index in sorted(
            associations,
            key=lambda value: int(value) if str(value).isdigit() else str(value),
        ):
            association = associations[tunnel_index]
            base_label_values = [
                device_name,
                firewall_name,
                _label_value(association.get("tunnel_index")),
                _label_value(association.get("remote_gateway")),
                _label_value(association.get("direction")),
            ]

            for metric_name, (description, field_name) in numeric_metrics.items():
                number = _numeric_value(association.get(field_name))
                if number is None:
                    continue

                metric_samples.setdefault(
                    metric_name,
                    {
                        "description": description,
                        "label_names": base_label_names,
                        "samples": [],
                    },
                )
                metric_samples[metric_name]["samples"].append(
                    {
                        "label_values": base_label_values,
                        "value": number,
                    }
                )

            info_metric_name = "srx_ipsec_sa_info"
            metric_samples.setdefault(
                info_metric_name,
                {
                    "description": (
                        "Current IPsec SA identity and negotiated settings."
                    ),
                    "label_names": base_label_names + [
                        "spi",
                        "encryption_algorithm",
                        "authentication_algorithm",
                        "port",
                    ],
                    "samples": [],
                },
            )
            metric_samples[info_metric_name]["samples"].append(
                {
                    "label_values": base_label_values + [
                        _label_value(association.get("spi")),
                        _label_value(association.get("encryption_algorithm")),
                        _label_value(association.get("authentication_algorithm")),
                        _label_value(association.get("port")),
                    ],
                    "value": 1,
                }
            )

    def _collect_ike_security_association_detail_samples(
        self,
        metric_samples,
        device_name,
        firewall_name,
        ike_values,
    ):
        """Export detailed data for every dynamically discovered IKE SA."""

        summary_metrics = {
            "srx_ike_detail_discovered_total": (
                "Number of IKE indices discovered by the summary RPC.",
                ike_values.get("discovered_total"),
            ),
            "srx_ike_detail_collected_total": (
                "Number of IKE detail records collected successfully.",
                ike_values.get("collected_total"),
            ),
            "srx_ike_detail_query_failures_total": (
                "Number of per-index IKE detail RPC failures in the latest collection cycle.",
                ike_values.get("query_failures_total"),
            ),
        }

        for metric_name, (description, raw_value) in summary_metrics.items():
            number = _numeric_value(raw_value)
            if number is None:
                continue
            if metric_name not in metric_samples:
                metric_samples[metric_name] = {
                    "description": description,
                    "label_names": ["device", "firewall"],
                    "samples": [],
                }
            metric_samples[metric_name]["samples"].append(
                {
                    "label_values": [device_name, firewall_name],
                    "value": number,
                }
            )

        associations = ike_values.get("associations", {})
        stable_label_names = [
            "device",
            "firewall",
            "ike_index",
            "gateway",
            "local_address",
            "remote_address",
            "ike_version",
            "exchange_type",
        ]

        numeric_metrics = {
            "srx_ike_detail_up": (
                "Whether the detailed IKE SA is currently in UP state.",
                "up",
            ),
            "srx_ike_detail_remaining_lifetime_seconds": (
                "Remaining IKE SA lifetime in seconds.",
                "remaining_lifetime_seconds",
            ),
            "srx_ike_detail_packets_in_total": (
                "Packets received by the IKE SA.",
                "packets_in",
            ),
            "srx_ike_detail_packets_out_total": (
                "Packets sent by the IKE SA.",
                "packets_out",
            ),
            "srx_ike_detail_bytes_in_total": (
                "Bytes received by the IKE SA.",
                "bytes_in",
            ),
            "srx_ike_detail_bytes_out_total": (
                "Bytes sent by the IKE SA.",
                "bytes_out",
            ),
            "srx_ike_detail_ipsec_sa_created_total": (
                "IPsec SAs created through the IKE SA.",
                "ipsec_sa_created",
            ),
            "srx_ike_detail_ipsec_sa_deleted_total": (
                "IPsec SAs deleted through the IKE SA.",
                "ipsec_sa_deleted",
            ),
            "srx_ike_detail_phase2_negotiations_total": (
                "Phase 2 negotiations recorded for the IKE SA.",
                "phase2_negotiations",
            ),
            "srx_ike_detail_phase2_failures_total": (
                "Failed Phase 2 negotiations recorded for the IKE SA.",
                "phase2_failures",
            ),
            "srx_ike_detail_rekeys_total": (
                "Rekeys recorded for the IKE SA.",
                "rekey_count",
            ),
            "srx_ike_detail_associated_tunnels": (
                "Number of associated IPsec tunnel identifiers.",
                "associated_tunnel_count",
            ),
        }

        for ike_index in sorted(
            associations,
            key=lambda value: int(value) if str(value).isdigit() else str(value),
        ):
            association = associations[ike_index]
            stable_label_values = [
                device_name,
                firewall_name,
                _label_value(association.get("ike_index")),
                _label_value(association.get("gateway")),
                _label_value(association.get("local_address")),
                _label_value(association.get("remote_address")),
                _label_value(association.get("ike_version")),
                _label_value(association.get("exchange_type")),
            ]

            for metric_name, (description, field_name) in numeric_metrics.items():
                number = _numeric_value(association.get(field_name))
                if number is None:
                    continue
                if metric_name not in metric_samples:
                    metric_samples[metric_name] = {
                        "description": description,
                        "label_names": stable_label_names,
                        "samples": [],
                    }
                metric_samples[metric_name]["samples"].append(
                    {
                        "label_values": stable_label_values,
                        "value": number,
                    }
                )

            info_metric_name = "srx_ike_detail_info"
            if info_metric_name not in metric_samples:
                metric_samples[info_metric_name] = {
                    "description": "Detailed IKE SA identity and negotiated settings.",
                    "label_names": stable_label_names + [
                        "state",
                        "authentication_method",
                        "encryption_algorithm",
                        "authentication_algorithm",
                        "prf_algorithm",
                        "dh_group",
                        "associated_tunnel_ids",
                    ],
                    "samples": [],
                }
            metric_samples[info_metric_name]["samples"].append(
                {
                    "label_values": stable_label_values + [
                        _label_value(association.get("state")),
                        _label_value(association.get("authentication_method")),
                        _label_value(association.get("encryption_algorithm")),
                        _label_value(association.get("authentication_algorithm")),
                        _label_value(association.get("prf_algorithm")),
                        _label_value(association.get("dh_group")),
                        _label_value(association.get("associated_tunnel_ids")),
                    ],
                    "value": 1,
                }
            )

    def _collect_ike_security_association_samples(
        self,
        metric_samples,
        device_name,
        firewall_name,
        ike_values,
    ):
        """Export IKE SA totals and per-SA state."""

        summaries = {
            "srx_ike_sa_total": (
                "Current number of IKE security associations.",
                ike_values.get("sa_total"),
            ),
            "srx_ike_sa_up_total": (
                "Current number of IKE security associations in UP state.",
                ike_values.get("sa_up_total"),
            ),
            "srx_ike_sa_down_total": (
                "Current number of IKE security associations not UP.",
                ike_values.get("sa_down_total"),
            ),
        }

        for metric_name, (description, raw_value) in summaries.items():
            value = _numeric_value(raw_value)
            if value is None:
                continue
            metric_samples.setdefault(
                metric_name,
                {
                    "description": description,
                    "label_names": ["device", "firewall"],
                    "samples": [],
                },
            )["samples"].append(
                {
                    "label_values": [device_name, firewall_name],
                    "value": value,
                }
            )

        associations = ike_values.get("associations", {})
        for ike_index in sorted(associations, key=str):
            association = associations[ike_index]
            base_labels = [
                device_name,
                firewall_name,
                _label_value(association.get("ike_index")),
                _label_value(association.get("remote_address")),
                _label_value(association.get("exchange_type")),
            ]

            metric_samples.setdefault(
                "srx_ike_sa_up",
                {
                    "description": "Whether the IKE SA is UP.",
                    "label_names": [
                        "device",
                        "firewall",
                        "ike_index",
                        "remote_address",
                        "exchange_type",
                    ],
                    "samples": [],
                },
            )["samples"].append(
                {
                    "label_values": base_labels,
                    "value": _numeric_value(association.get("up")),
                }
            )

            metric_samples.setdefault(
                "srx_ike_sa_info",
                {
                    "description": "IKE SA identity and raw state.",
                    "label_names": [
                        "device",
                        "firewall",
                        "ike_index",
                        "remote_address",
                        "exchange_type",
                        "state",
                    ],
                    "samples": [],
                },
            )["samples"].append(
                {
                    "label_values": base_labels + [
                        _label_value(association.get("state"))
                    ],
                    "value": 1,
                }
            )

    def _collect_ha_info(
        self,
        metric_samples,
        device_name,
        ha_values,
    ):
        """
        Export MNHA state as both labels and a numeric role value.

        Role-state values:
            2 = ACTIVE
            1 = BACKUP or STANDBY
            0 = DOWN, FAILED, OFFLINE or unknown
        """

        info_metric_name = "srx_ha_info"

        if info_metric_name not in metric_samples:
            metric_samples[info_metric_name] = {
                "description": (
                    "Juniper SRX Multi-Node High Availability information."
                ),
                "label_names": [
                    "device",
                    "node_status",
                    "role",
                    "peer_role",
                    "health",
                    "failover_readiness",
                    "control_plane_state",
                    "cold_sync_status",
                    "peer_bfd",
                ],
                "samples": [],
            }

        metric_samples[info_metric_name]["samples"].append(
            {
                "label_values": [
                    device_name,
                    _label_value(ha_values.get("node_status")),
                    _label_value(ha_values.get("role")),
                    _label_value(ha_values.get("peer_role")),
                    _label_value(ha_values.get("health")),
                    _label_value(ha_values.get("failover_readiness")),
                    _label_value(ha_values.get("control_plane_state")),
                    _label_value(ha_values.get("cold_sync_status")),
                    _label_value(ha_values.get("peer_bfd")),
                ],
                "value": 1,
            }
        )

        role = _label_value(
            ha_values.get("role")
        ).upper()

        node_status = _label_value(
            ha_values.get("node_status")
        ).upper()

        if node_status not in {"ONLINE", "UP"}:
            role_state = 0
        elif role == "ACTIVE":
            role_state = 2
        elif role in {"BACKUP", "STANDBY"}:
            role_state = 1
        else:
            role_state = 0

        role_metric_name = "srx_ha_role_state"

        if role_metric_name not in metric_samples:
            metric_samples[role_metric_name] = {
                "description": (
                    "MNHA role state: 2 active, 1 backup or standby, "
                    "0 down or unknown."
                ),
                "label_names": ["device"],
                "samples": [],
            }

        metric_samples[role_metric_name]["samples"].append(
            {
                "label_values": [device_name],
                "value": role_state,
            }
        )

    def _collect_system_info(
        self,
        metric_samples,
        device_name,
        system_values,
    ):
        """
        Export static Juniper system information as Prometheus labels.

        Prometheus does not store arbitrary string metric values. Static
        identity information is therefore exported as labels on a gauge
        whose value is always 1.
        """

        metric_name = "srx_system_info"

        if metric_name not in metric_samples:
            metric_samples[metric_name] = {
                "description": (
                    "Static system information reported by the Juniper SRX."
                ),
                "label_names": [
                    "device",
                    "hostname",
                    "model",
                    "family",
                    "junos_version",
                    "serial_number",
                ],
                "samples": [],
            }

        metric_samples[metric_name]["samples"].append(
            {
                "label_values": [
                    _label_value(device_name),
                    _label_value(system_values.get("hostname")),
                    _label_value(system_values.get("model")),
                    _label_value(system_values.get("family")),
                    _label_value(system_values.get("version")),
                    _label_value(system_values.get("serial")),
                ],
                "value": 1,
            }
        )

    def _collect_security_screen_samples(
        self,
        metric_samples,
        device_name,
        zones,
    ):
        """Export Screen counters with device and zone labels."""

        for zone_name, zone_values in zones.items():
            for path, value in _flatten_numeric_metrics(zone_values):
                if not path:
                    continue
                metric_name = "srx_screen_{}".format("_".join(path))
                self._add_sample(
                    metric_samples=metric_samples,
                    metric_name=metric_name,
                    label_names=["device", "zone"],
                    label_values=[device_name, zone_name],
                    value=value,
                )

    def _collect_security_policy_hit_count_samples(
        self,
        metric_samples,
        device_name,
        policies,
    ):
        """Export one dynamically labelled sample per security policy."""

        for policy_values in policies.values():
            self._add_sample(
                metric_samples=metric_samples,
                metric_name="srx_security_policy_hit_count_total",
                label_names=[
                    "device",
                    "logical_system",
                    "from_zone",
                    "to_zone",
                    "policy",
                    "action",
                ],
                label_values=[
                    device_name,
                    policy_values.get("logical_system", "root-logical-system"),
                    policy_values.get("from_zone", ""),
                    policy_values.get("to_zone", ""),
                    policy_values.get("policy", ""),
                    policy_values.get("action", ""),
                ],
                value=policy_values.get("hit_count_total", 0),
            )

    def _collect_system_alarms_samples(
        self,
        metric_samples,
        device_name,
        alarms_section,
    ):
        """Export active alarm count and one sample per active alarm."""

        self._add_sample(
            metric_samples=metric_samples,
            metric_name="srx_system_alarm_active_count",
            label_names=["device"],
            label_values=[device_name],
            value=alarms_section.get("active_alarm_count", 0),
        )

        for alarm_values in alarms_section.get("alarms", {}).values():
            label_names = [
                "device",
                "alarm_class",
                "alarm_type",
                "alarm_short_description",
            ]
            label_values = [
                device_name,
                alarm_values.get("alarm_class", ""),
                alarm_values.get("alarm_type", ""),
                alarm_values.get("alarm_short_description", ""),
            ]

            self._add_sample(
                metric_samples=metric_samples,
                metric_name="srx_system_alarm_active",
                label_names=label_names,
                label_values=label_values,
                value=alarm_values.get("active", 1),
            )

            self._add_sample(
                metric_samples=metric_samples,
                metric_name="srx_system_alarm_raised_timestamp_seconds",
                label_names=label_names,
                label_values=label_values,
                value=alarm_values.get("raised_timestamp_seconds", 0),
            )

    def _collect_section_samples(
        self,
        metric_samples,
        device_name,
        section_name,
        section_values,
    ):
        """
        Translate a non-interface collector section.
        """

        section_component = _sanitize_metric_name(section_name)

        for path, value in _flatten_numeric_metrics(section_values):
            if not path:
                continue

            metric_name = "srx_{}_{}".format(
                section_component,
                "_".join(path),
            )

            self._add_sample(
                metric_samples=metric_samples,
                metric_name=metric_name,
                label_names=["device"],
                label_values=[device_name],
                value=value,
            )

    def _collect_interface_samples(
        self,
        metric_samples,
        device_name,
        interfaces,
    ):
        """
        Translate interface metrics.

        Each interface is exported with device and interface labels.
        """

        for interface_name, interface_values in interfaces.items():

            for path, value in _flatten_numeric_metrics(interface_values):
                if not path:
                    continue

                metric_name = "srx_interface_{}".format(
                    "_".join(path)
                )

                self._add_sample(
                    metric_samples=metric_samples,
                    metric_name=metric_name,
                    label_names=["device", "interface"],
                    label_values=[
                        device_name,
                        interface_name,
                    ],
                    value=value,
                )

    @staticmethod
    def _add_sample(
        metric_samples,
        metric_name,
        label_names,
        label_values,
        value,
    ):
        """
        Add a sample to its metric family.
        """

        if metric_name not in metric_samples:
            metric_samples[metric_name] = {
                "description": (
                    "Metric collected from a Juniper SRX using NETCONF."
                ),
                "label_names": label_names,
                "samples": [],
            }

        metric_samples[metric_name]["samples"].append(
            {
                "label_values": label_values,
                "value": value,
            }
        )
