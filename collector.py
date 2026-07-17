import yaml

from netconf import NetconfClient
from parser import (
    get_system_information,
    get_ha_information,
)


def load_config():
    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)


def main():

    config = load_config()

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

        metrics["system"] = get_system_information(client.conn)
        metrics["ha"] = get_ha_information(client.conn)

        client.disconnect()

        print("\nCollected Metrics")
        print("-----------------")

        for section, values in metrics.items():

            print(f"\n[{section}]")

            for key, value in values.items():
                print(f"{key:20} {value}")


if __name__ == "__main__":
    main()
