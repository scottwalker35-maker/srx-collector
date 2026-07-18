"""
Test NETCONF connectivity using the first device in config.yaml.

No credentials are stored in this file.
"""

import sys

import yaml
from ncclient import manager


def load_first_device(config_path="config.yaml"):
    """
    Load and validate the first configured device.
    """

    with open(config_path, "r", encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file) or {}

    devices = config.get("devices", [])

    if not devices:
        raise RuntimeError(
            f"No devices are configured in {config_path}"
        )

    device = devices[0]

    required = ("host", "username", "password")

    missing = [
        key
        for key in required
        if not str(device.get(key, "")).strip()
    ]

    if missing:
        raise RuntimeError(
            "Missing required device values: "
            + ", ".join(missing)
        )

    return device


def main():
    """
    Connect to the first configured SRX and print capabilities.
    """

    device = load_first_device()

    host = str(device["host"])
    port = int(device.get("port", 830))
    username = str(device["username"])
    password = str(device["password"])

    print(f"Connecting to {host}:{port}...")

    with manager.connect(
        host=host,
        port=port,
        username=username,
        password=password,
        hostkey_verify=False,
        device_params={"name": "junos"},
        allow_agent=False,
        look_for_keys=False,
        timeout=30,
    ) as connection:

        print("Connected.")
        print("Server capabilities:")

        for capability in connection.server_capabilities:
            print(capability)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"NETCONF test failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
