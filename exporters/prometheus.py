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

                if section_name == "interface_statistics":
                    self._collect_interface_samples(
                        metric_samples=metric_samples,
                        device_name=device_name,
                        interfaces=section_values,
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
                    "readiness",
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
                    _label_value(ha_values.get("readiness")),
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
