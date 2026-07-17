import yaml

from lib.netconf import NetconfClient

from collectors.system import collect_system
from collectors.ha import collect_ha
from collectors.sessions import collect_sessions
from collectors.route_engine import collect_route_engine
from collectors.interface_statistics import collect_interface_statistics


def load_config():
    """
    Load the collector configuration.
    """

    with open("config.yaml", "r", encoding="utf-8") as config_file:
        return yaml.safe_load(config_file)


def print_nested(value, indent=0):
    """
    Print nested dictionaries returned by collectors.
    """

    prefix = " " * indent

    if isinstance(value, dict):
        for key, child_value in value.items():

            if isinstance(child_value, dict):
                print(f"{prefix}{key}")
                print_nested(child_value, indent + 4)
                continue

            child_value = (
                ""
                if child_value is None
                else str(child_value).strip()
            )

            print(
                f"{prefix}{key:35} "
                f"{child_value}"
            )

        return

    print(f"{prefix}{value}")


def collect_device_metrics(client, device):
    """
    Run all collectors for one device.

    Interface collection receives the device-specific list of selected
    parent interfaces. Selecting a parent includes all logical units
    beneath that parent.
    """

    metrics = {}

    standard_collectors = (
        collect_system,
        collect_ha,
        collect_sessions,
        collect_route_engine,
    )

    for collector in standard_collectors:
        result = collector(client)
        metrics[result["name"]] = result["metrics"]

    interface_result = collect_interface_statistics(
        client=client,
        selected_interfaces=device.get("interfaces", []),
    )

    metrics[interface_result["name"]] = interface_result["metrics"]

    return metrics


def print_metrics(metrics):
    """
    Print all collected metrics.
    """

    print("\nCollected Metrics")
    print("-----------------")

    for section, values in metrics.items():

        print(f"\n[{section}]")

        if section == "interface_statistics":

            print(
                f"{'interfaces_collected':35} "
                f"{len(values)}"
            )

            for interface_name, interface_values in values.items():

                print(f"\n{interface_name}")

                print_nested(
                    interface_values,
                    indent=4,
                )

            continue

        for key, value in values.items():

            value = (
                ""
                if value is None
                else str(value).strip()
            )

            print(f"{key:35} {value}")


def main():
    """
    Main collector entry point.
    """

    config = load_config()

    for device in config["devices"]:

        print(f"\nConnecting to {device['name']}...")

        client = NetconfClient(
            host=device["host"],
            username=device["username"],
            password=device["password"],
            port=device["port"],
        )

        try:
            client.connect()

            metrics = collect_device_metrics(
                client=client,
                device=device,
            )

        finally:
            client.disconnect()

        print_metrics(metrics)


if __name__ == "__main__":
    main()
