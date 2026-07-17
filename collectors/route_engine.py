"""
Collector: Route Engine

CLI:
    show chassis routing-engine

RPC:
    get-route-engine-information

Metrics:
    - model

    - memory_system_total_mb
    - memory_system_used_mb
    - memory_system_util

    - memory_control_plane_mb
    - memory_control_plane_used_mb
    - memory_control_plane_util

    - memory_data_plane_mb
    - memory_data_plane_used_mb
    - memory_data_plane_util

    - cpu_user
    - cpu_background
    - cpu_system
    - cpu_interrupt
    - cpu_idle

    - start_time
    - uptime
    - last_reboot_reason

    - load_average_1
    - load_average_5
    - load_average_15
"""

from lxml import etree


def collect_route_engine(client):

    rpc = etree.XML("<get-route-engine-information/>")

    reply = client.conn.dispatch(rpc)

    if hasattr(reply, "xml"):
        root = etree.fromstring(reply.xml.encode())
    elif hasattr(reply, "data_xml"):
        root = etree.fromstring(reply.data_xml.encode())
    elif hasattr(reply, "_NCElement__doc"):
        root = reply._NCElement__doc.getroot()
    else:
        raise RuntimeError(f"Unsupported reply type: {type(reply)}")

    return {
        "name": "route_engine",
        "metrics": {

            "model":
                root.findtext(".//model"),

            "memory_system_total_mb":
                root.findtext(".//memory-system-total"),

            "memory_system_used_mb":
                root.findtext(".//memory-system-total-used"),

            "memory_system_util":
                root.findtext(".//memory-system-total-util"),

            "memory_control_plane_mb":
                root.findtext(".//memory-control-plane"),

            "memory_control_plane_used_mb":
                root.findtext(".//memory-control-plane-used"),

            "memory_control_plane_util":
                root.findtext(".//memory-control-plane-util"),

            "memory_data_plane_mb":
                root.findtext(".//memory-data-plane"),

            "memory_data_plane_used_mb":
                root.findtext(".//memory-data-plane-used"),

            "memory_data_plane_util":
                root.findtext(".//memory-data-plane-util"),

            "cpu_user":
                root.findtext(".//cpu-user"),

            "cpu_background":
                root.findtext(".//cpu-background"),

            "cpu_system":
                root.findtext(".//cpu-system"),

            "cpu_interrupt":
                root.findtext(".//cpu-interrupt"),

            "cpu_idle":
                root.findtext(".//cpu-idle"),

            "start_time":
                root.findtext(".//start-time"),

            "uptime":
                root.findtext(".//up-time"),

            "last_reboot_reason":
                root.findtext(".//last-reboot-reason"),

            "load_average_1":
                root.findtext(".//load-average-one"),

            "load_average_5":
                root.findtext(".//load-average-five"),

            "load_average_15":
                root.findtext(".//load-average-fifteen"),
        },
    }
