"""
Collector: High Availability

CLI:
    show chassis high-availability

RPC:
    get-chassis-high-availability-information
"""


def collect_ha(client):

    root = client.rpc("get-chassis-high-availability-information")

    return {
        "name": "ha",
        "metrics": {
            "node_status": root.findtext(".//node-status"),
            "role": root.findtext(".//node-role"),
            "peer_role": root.findtext(".//peer-node-role"),
            "health": root.findtext(".//health-status"),
            "failover_readiness": root.findtext(".//failover-readiness"),
            "control_plane_state": root.findtext(".//control-plane-state"),
            "cold_sync_status": root.findtext(".//cold-sync-status"),
            "peer_bfd": root.findtext(".//high-availability-peer-bfd-status"),
        },
    }
