"""
Collector: Interface Statistics

CLI:
    show interfaces extensive

RPC:
    get-interface-information extensive

Collects selected physical interfaces and every logical interface beneath
each selected parent.

The selected parent interfaces are supplied through config.yaml.

Example:

    interfaces:
      - ge-0/0/0
      - ge-0/0/1
      - fxp0
      - st0

Selecting ge-0/0/0 includes:

    ge-0/0/0
    ge-0/0/0.0
    ge-0/0/0.100

IP addresses and host-inbound service configuration are intentionally excluded.
"""

from lxml import etree


def _text(node, path, default=""):
    """
    Return cleaned text from an XML element.
    """

    value = node.findtext(path)

    if value is None:
        return default

    return str(value).strip()


def _integer(node, path, default=0):
    """
    Return an integer from an XML element.

    Junos may return counters containing commas or whitespace.
    """

    value = _text(node, path, "")

    if value == "":
        return default

    value = value.replace(",", "")

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _status_value(value):
    """
    Convert Junos interface status text into a numeric value.

    up/running/ready/online = 1
    down                    = 0
    missing/unknown         = None

    A missing status must not be reported as down.
    """

    normalized = str(value or "").strip().lower()

    if normalized == "":
        return None

    if normalized in {"up", "running", "ready", "online"}:
        return 1

    if normalized in {"down", "offline", "not-ready"}:
        return 0

    return None


def _normalize_selected_interfaces(selected_interfaces):
    """
    Normalize the configured list of selected parent interfaces.
    """

    normalized = []

    for interface_name in selected_interfaces or []:

        interface_name = str(interface_name).strip()

        if interface_name and interface_name not in normalized:
            normalized.append(interface_name)

    return normalized


def _physical_interface_selected(
    physical_name,
    selected_interfaces,
):
    """
    Determine whether a physical interface was explicitly selected.

    Selection is exact at the parent level. Once selected, every logical
    interface beneath the parent is included automatically.

    Example:

        selected parent: ge-0/0/0

        included:
            ge-0/0/0
            ge-0/0/0.0
            ge-0/0/0.100

        not included:
            ge-0/0/1
    """

    return physical_name in selected_interfaces


def _dispatch_interface_rpc(client):
    """
    Execute:

        <get-interface-information>
            <extensive/>
        </get-interface-information>

    The existing NetconfClient.rpc() helper currently supports RPCs without
    child elements, so this collector dispatches the extensive RPC directly.
    """

    rpc = etree.XML(
        """
        <get-interface-information>
            <extensive/>
        </get-interface-information>
        """
    )

    reply = client.conn.dispatch(rpc)

    if hasattr(reply, "xml"):
        return etree.fromstring(reply.xml.encode())

    if hasattr(reply, "data_xml"):
        return etree.fromstring(reply.data_xml.encode())

    if hasattr(reply, "_NCElement__doc"):
        return reply._NCElement__doc.getroot()

    raise RuntimeError(
        f"Unsupported ncclient reply type: {type(reply)}"
    )


def _parse_physical_errors(node):
    """
    Parse common physical-interface error counters.
    """

    return {
        "input_errors":
            _integer(node, "input-error-list/input-errors"),

        "input_drops":
            _integer(node, "input-error-list/input-drops"),

        "input_framing_errors":
            _integer(node, "input-error-list/framing-errors"),

        "input_runts":
            _integer(node, "input-error-list/input-runts"),

        "input_giants":
            _integer(node, "input-error-list/input-giants"),

        "input_resource_errors":
            _integer(node, "input-error-list/resource-errors"),

        "input_fifo_errors":
            _integer(node, "input-error-list/input-fifo-errors"),

        "output_errors":
            _integer(node, "output-error-list/output-errors"),

        "output_drops":
            _integer(node, "output-error-list/output-drops"),

        "output_collisions":
            _integer(node, "output-error-list/output-collisions"),

        "output_carrier_transitions":
            _integer(node, "output-error-list/carrier-transitions"),

        "output_fifo_errors":
            _integer(node, "output-error-list/output-fifo-errors"),

        "output_mtu_errors":
            _integer(node, "output-error-list/output-mtu-errors"),

        "output_resource_errors":
            _integer(node, "output-error-list/output-resource-errors"),
    }


def _parse_physical_traffic(node):
    """
    Parse cumulative and instantaneous physical-interface traffic counters.
    """

    return {
        "rx_bytes_total":
            _integer(node, "traffic-statistics/input-bytes"),

        "tx_bytes_total":
            _integer(node, "traffic-statistics/output-bytes"),

        "rx_packets_total":
            _integer(node, "traffic-statistics/input-packets"),

        "tx_packets_total":
            _integer(node, "traffic-statistics/output-packets"),

        "rx_bps":
            _integer(node, "traffic-statistics/input-bps"),

        "tx_bps":
            _integer(node, "traffic-statistics/output-bps"),

        "rx_pps":
            _integer(node, "traffic-statistics/input-pps"),

        "tx_pps":
            _integer(node, "traffic-statistics/output-pps"),
    }


def _parse_queue_statistics(node):
    """
    Parse interface queue counters.

    Queue information is returned as a dictionary keyed by queue number.
    """

    queues = {}

    queue_nodes = node.findall(".//queue-counters/queue")

    for queue_node in queue_nodes:

        queue_number = _text(queue_node, "queue-number")

        if queue_number == "":
            continue

        queues[queue_number] = {
            "queued_packets_total":
                _integer(queue_node, "queued-packets"),

            "queued_bytes_total":
                _integer(queue_node, "queued-bytes"),

            "transmitted_packets_total":
                _integer(queue_node, "transmitted-packets"),

            "transmitted_bytes_total":
                _integer(queue_node, "transmitted-bytes"),

            "tail_drop_packets_total":
                _integer(queue_node, "tail-drop-packets"),

            "red_drop_packets_total":
                _integer(queue_node, "red-drop-packets"),

            "rate_limit_drop_packets_total":
                _integer(queue_node, "rate-limit-drop-packets"),
        }

    return queues


def _parse_security_group(node, group_name):
    """
    Parse one logical-interface security statistics group.

    Junos returns different counters depending on platform and Junos release.
    This dynamically collects every numeric child counter in the group.
    """

    statistics = {}

    group = node.find(group_name)

    if group is None:
        return statistics

    for child in group:

        tag = etree.QName(child).localname
        value = "" if child.text is None else child.text.strip()

        if value == "":
            continue

        try:
            statistics[tag.replace("-", "_")] = int(
                value.replace(",", "")
            )
        except ValueError:
            continue

    return statistics


def _parse_logical_traffic(node):
    """
    Parse logical-interface traffic counters.
    """

    return {
        "rx_bytes_total":
            _integer(node, "traffic-statistics/input-bytes"),

        "tx_bytes_total":
            _integer(node, "traffic-statistics/output-bytes"),

        "rx_packets_total":
            _integer(node, "traffic-statistics/input-packets"),

        "tx_packets_total":
            _integer(node, "traffic-statistics/output-packets"),

        "local_rx_bytes_total":
            _integer(
                node,
                "local-traffic-statistics/input-bytes"
            ),

        "local_tx_bytes_total":
            _integer(
                node,
                "local-traffic-statistics/output-bytes"
            ),

        "local_rx_packets_total":
            _integer(
                node,
                "local-traffic-statistics/input-packets"
            ),

        "local_tx_packets_total":
            _integer(
                node,
                "local-traffic-statistics/output-packets"
            ),

        "transit_rx_bytes_total":
            _integer(
                node,
                "transit-traffic-statistics/input-bytes"
            ),

        "transit_tx_bytes_total":
            _integer(
                node,
                "transit-traffic-statistics/output-bytes"
            ),

        "transit_rx_packets_total":
            _integer(
                node,
                "transit-traffic-statistics/input-packets"
            ),

        "transit_tx_packets_total":
            _integer(
                node,
                "transit-traffic-statistics/output-packets"
            ),
    }


def _parse_logical_interface(
    node,
    parent_name,
    parent_description,
):
    """
    Parse one logical interface.

    Junos does not always return explicit admin or operational status for
    logical interfaces. Missing status is represented as None instead of 0.
    """

    name = _text(node, "name")

    description = _text(node, "description")

    if description == "":
        description = parent_description

    admin_status = _text(node, "admin-status")
    oper_status = _text(node, "oper-status")

    vlan = _text(node, "link-address")

    if vlan == "":
        vlan = _text(node, "vlan-tag")

    interface_type = _text(node, "encapsulation")

    if interface_type == "":
        interface_type = "logical"

    return {
        "interface": name,
        "parent": parent_name,
        "interface_type": interface_type,
        "description": description,
        "zone": _text(node, "logical-interface-zone-name"),
        "vlan": vlan,
        "admin_status": admin_status,
        "admin_up": _status_value(admin_status),
        "oper_status": oper_status,
        "oper_up": _status_value(oper_status),
        "snmp_index": _integer(node, "snmp-index"),
        "local_index": _integer(node, "local-index"),
        "traffic": _parse_logical_traffic(node),

        "security_input":
            _parse_security_group(
                node,
                "security-input-flow-statistics"
            ),

        "security_output":
            _parse_security_group(
                node,
                "security-output-flow-statistics"
            ),

        "security_errors":
            _parse_security_group(
                node,
                "security-error-flow-statistics"
            ),
    }


def _parse_physical_interface(node):
    """
    Parse one physical interface.
    """

    name = _text(node, "name")
    description = _text(node, "description")
    admin_status = _text(node, "admin-status")
    oper_status = _text(node, "oper-status")

    return {
        "interface": name,
        "parent": "",
        "interface_type":
            _text(node, "link-level-type", "physical"),

        "description": description,
        "zone": "",
        "vlan": "",
        "admin_status": admin_status,
        "admin_up": _status_value(admin_status),
        "oper_status": oper_status,
        "oper_up": _status_value(oper_status),
        "speed": _text(node, "speed"),
        "mtu": _integer(node, "mtu"),
        "encapsulation": _text(node, "encapsulation"),
        "snmp_index": _integer(node, "snmp-index"),
        "mac_address":
            _text(node, "current-physical-address"),

        "last_flapped":
            _text(node, "interface-flapped"),

        "traffic":
            _parse_physical_traffic(node),

        "errors":
            _parse_physical_errors(node),

        "queues":
            _parse_queue_statistics(node),
    }


def collect_interface_statistics(
    client,
    selected_interfaces=None,
):
    """
    Collect selected physical interfaces and their logical units.

    Return format:

        {
            "name": "interface_statistics",
            "metrics": {
                "ge-0/0/0": {
                    ...
                },
                "ge-0/0/0.100": {
                    ...
                }
            }
        }

    A selected physical interface automatically includes every logical
    interface beneath it.

    Selecting:

        ge-0/0/0

    includes:

        ge-0/0/0
        ge-0/0/0.0
        ge-0/0/0.100
    """

    selected_interfaces = _normalize_selected_interfaces(
        selected_interfaces
    )

    root = _dispatch_interface_rpc(client)

    metrics = {}

    for physical_node in root.findall(".//physical-interface"):

        physical_name = _text(physical_node, "name")

        if not physical_name:
            continue

        if not _physical_interface_selected(
            physical_name=physical_name,
            selected_interfaces=selected_interfaces,
        ):
            continue

        physical = _parse_physical_interface(physical_node)

        metrics[physical_name] = physical

        parent_description = physical["description"]

        for logical_node in physical_node.findall(
            "logical-interface"
        ):

            logical = _parse_logical_interface(
                node=logical_node,
                parent_name=physical_name,
                parent_description=parent_description,
            )

            logical_name = logical["interface"]

            if logical_name:
                metrics[logical_name] = logical

    return {
        "name": "interface_statistics",
        "metrics": metrics,
    }
