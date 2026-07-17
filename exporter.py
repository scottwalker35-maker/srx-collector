import logging
import threading
import time

from prometheus_client import CollectorRegistry
from prometheus_client import start_http_server

from collector import collect_device_metrics
from collector import load_config
from exporters.prometheus import SrxPrometheusCollector
from lib.netconf import NetconfClient


LOGGER = logging.getLogger("srx-exporter")


def configure_logging():
    """
    Configure exporter logging while suppressing verbose SSH and NETCONF logs.
    """

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s %(levelname)s "
            "%(name)s: %(message)s"
        ),
    )

    logging.getLogger("ncclient").setLevel(logging.WARNING)
    logging.getLogger("paramiko").setLevel(logging.WARNING)


def get_device_id(device):
    """
    Return the stable exporter identity for a configured device.

    The OAM address is used because it is known before NETCONF collection
    begins and does not depend on the configured Junos hostname.
    """

    return str(device["host"])


def collect_device(device, prometheus_collector):
    """
    Connect to one SRX, run all collectors and update the metric cache.
    """

    device_id = get_device_id(device)
    started_at = time.monotonic()

    client = NetconfClient(
        host=device["host"],
        username=device["username"],
        password=device["password"],
        port=device.get("port", 830),
    )

    connected = False

    try:
        LOGGER.info(
            "Connecting to SRX at %s:%s",
            device["host"],
            device.get("port", 830),
        )

        client.connect()
        connected = True

        metrics = collect_device_metrics(
            client=client,
            device=device,
        )

        duration_seconds = time.monotonic() - started_at

        prometheus_collector.update_device(
            device_name=device_id,
            metrics=metrics,
            duration_seconds=duration_seconds,
        )

        hostname = (
            metrics.get("system", {}).get("hostname")
            or "unknown"
        )

        LOGGER.info(
            "Collected %s at %s successfully in %.2f seconds",
            hostname,
            device["host"],
            duration_seconds,
        )

    except Exception:
        duration_seconds = time.monotonic() - started_at

        prometheus_collector.mark_device_error(
            device_name=device_id,
            duration_seconds=duration_seconds,
        )

        LOGGER.exception(
            "Collection failed for %s after %.2f seconds",
            device["host"],
            duration_seconds,
        )

    finally:
        if connected:
            try:
                client.disconnect()
            except Exception:
                LOGGER.warning(
                    "Failed to disconnect cleanly from %s",
                    device["host"],
                    exc_info=True,
                )


def collection_loop(
    devices,
    prometheus_collector,
    interval_seconds,
):
    """
    Continuously collect all configured SRX devices.
    """

    while True:
        cycle_started_at = time.monotonic()

        for device in devices:
            collect_device(
                device=device,
                prometheus_collector=prometheus_collector,
            )

        cycle_duration = time.monotonic() - cycle_started_at

        sleep_seconds = max(
            0,
            interval_seconds - cycle_duration,
        )

        LOGGER.info(
            "Collection cycle completed in %.2f seconds; "
            "sleeping %.2f seconds",
            cycle_duration,
            sleep_seconds,
        )

        time.sleep(sleep_seconds)


def main():
    """
    Start the SRX Prometheus exporter.
    """

    configure_logging()

    config = load_config()

    exporter_config = config.get("exporter", {})

    listen_address = exporter_config.get(
        "listen_address",
        "0.0.0.0",
    )

    listen_port = int(
        exporter_config.get(
            "listen_port",
            9105,
        )
    )

    interval_seconds = int(
        exporter_config.get(
            "collection_interval_seconds",
            30,
        )
    )

    if interval_seconds < 1:
        raise ValueError(
            "collection_interval_seconds must be at least 1"
        )

    devices = config.get("devices", [])

    if not devices:
        raise RuntimeError(
            "No devices are configured in config.yaml"
        )

    for device in devices:
        if "host" not in device:
            raise ValueError(
                "Every device requires a host value"
            )

    registry = CollectorRegistry()

    prometheus_collector = SrxPrometheusCollector()
    registry.register(prometheus_collector)

    collection_thread = threading.Thread(
        target=collection_loop,
        kwargs={
            "devices": devices,
            "prometheus_collector": prometheus_collector,
            "interval_seconds": interval_seconds,
        },
        daemon=True,
        name="srx-collection-loop",
    )

    collection_thread.start()

    start_http_server(
        port=listen_port,
        addr=listen_address,
        registry=registry,
    )

    LOGGER.info(
        "Prometheus exporter listening on http://%s:%s/metrics",
        listen_address,
        listen_port,
    )

    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        LOGGER.info("Exporter stopped by user.")


if __name__ == "__main__":
    main()
