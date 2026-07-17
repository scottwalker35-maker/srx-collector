"""
Collector: System Information

CLI:
    show system information

RPC:
    get-system-information
"""


def collect_system(client):

    root = client.rpc("get-system-information")

    return {
        "name": "system",
        "metrics": {
            "hostname": root.findtext(".//host-name"),
            "model": root.findtext(".//hardware-model"),
            "family": root.findtext(".//os-name"),
            "version": root.findtext(".//os-version"),
            "serial": root.findtext(".//serial-number"),
        },
    }
