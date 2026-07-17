import yaml

from lib.netconf import NetconfClient

from collectors.system import collect_system
from collectors.ha import collect_ha


def load_config():
    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)


def main():

    config = load_config()

    collectors = (
        collect_system,
        collect_ha,
    )

    for device in config["devices"]:

        print(f"\nConnecting to {device['name']}...")

        client = NetconfClient(
            host=device["host"],
            username=device["username"],
            password=device["password"],
            port=device["port"],
        )

        client.connect()

        metrics = {}

        #
        # Run every collector
        #
        for collector in collectors:

            result = collector(client)

            metrics[result["name"]] = result["metrics"]

        client.disconnect()

        print("\nCollected Metrics")
        print("-----------------")

        for section, values in metrics.items():

            print(f"\n[{section}]")

            for key, value in values.items():
                print(f"{key:20} {value}")


if __name__ == "__main__":
    main()
