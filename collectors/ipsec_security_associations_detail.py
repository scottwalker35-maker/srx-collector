"""
Collector: IPsec Security Association Detail

Junos CLI:
    show security ipsec security-associations detail index <tunnel-index>

XML RPC:
    <get-security-associations-information>
        <detail/>
        <show-index-ipsec-security-association>INDEX</show-index-ipsec-security-association>
    </get-security-associations-information>

Discovery RPC:
    <get-security-associations-information/>

The summary RPC dynamically discovers current tunnel indices. This collector
queries each index and normalizes tunnel identity, policy, interface, IKE
correlation, negotiated algorithms, lifetimes, replay settings, negotiation
statistics, and inbound/outbound SA records.
"""

import re
from lxml import etree


def _reply_root(reply):
    if hasattr(reply, "xml"):
        return etree.fromstring(reply.xml.encode())
    if hasattr(reply, "data_xml"):
        return etree.fromstring(reply.data_xml.encode())
    if hasattr(reply, "_NCElement__doc"):
        return reply._NCElement__doc.getroot()
    raise RuntimeError(f"Unsupported ncclient reply type: {type(reply)}")


def _local_name(element):
    return etree.QName(element).localname


def _first_text(root, *names, default=""):
    wanted = set(names)
    for element in root.iter():
        if _local_name(element) not in wanted or element.text is None:
            continue
        value = str(element.text).strip()
        if value:
            return value
    return default


def _number(value, default=0):
    if value is None:
        return default
    match = re.search(r"-?\d+(?:\.\d+)?", str(value).replace(",", ""))
    if not match:
        return default
    number = float(match.group(0))
    return int(number) if number.is_integer() else number


def _summary_indices(client):
    reply = client.conn.dispatch(
        etree.XML("<get-security-associations-information/>")
    )
    root = _reply_root(reply)
    indices = []

    for element in root.iter():
        if _local_name(element) != "sa-tunnel-index" or element.text is None:
            continue
        value = str(element.text).strip()
        if value and value not in indices:
            indices.append(value)

    return indices


def _detail_rpc(tunnel_index):
    rpc = etree.Element("get-security-associations-information")
    etree.SubElement(rpc, "detail")
    index_node = etree.SubElement(
        rpc,
        "show-index-ipsec-security-association",
    )
    index_node.text = str(tunnel_index)
    return rpc


def _parse_direction(node):
    direction = _first_text(node, "sa-direction")
    return {
        "direction": direction,
        "spi": _first_text(node, "sa-spi"),
        "aux_spi": _first_text(node, "sa-aux-spi"),
        "port": _number(_first_text(node, "sa-port")),
        "monitoring_state": _first_text(node, "sa-vpn-monitoring-state"),
        "esp_encryption_algorithm": _first_text(
            node,
            "sa-esp-encryption-algorithm",
        ),
        "hmac_algorithm": _first_text(node, "sa-hmac-algorithm"),
        "hard_lifetime_seconds": _number(
            _first_text(node, "sa-hard-lifetime")
        ),
        "soft_lifetime_seconds": _number(
            _first_text(node, "sa-soft-lifetime")
        ),
        "lifesize_remaining": _first_text(node, "sa-lifesize-remaining"),
        "mode": _first_text(node, "sa-mode"),
        "type": _first_text(node, "sa-type"),
        "state": _first_text(node, "sa-state"),
        "installed": 1 if _first_text(node, "sa-state").lower() == "installed" else 0,
        "protocol": _first_text(node, "sa-protocol"),
        "authentication_algorithm": _first_text(
            node,
            "sa-authentication-algorithm",
        ),
        "encryption_algorithm": _first_text(
            node,
            "sa-encryption-algorithm",
        ),
        "anti_replay_service": _first_text(
            node,
            "sa-anti-replay-service",
        ),
        "replay_window_size": _number(
            _first_text(node, "sa-replay-window-size")
        ),
        "extended_sequence_number": _first_text(
            node,
            "sa-extended-seq-number",
        ),
        "tunnel_establishment": _first_text(
            node,
            "sa-tunnel-establishment",
        ),
        "ike_index": _first_text(node, "sa-ike-index"),
    }


def _parse_detail(root, discovered_index):
    block = None
    for element in root.iter():
        if _local_name(element) == "ipsec-security-associations-block":
            block = element
            break

    if block is None:
        block = root

    directions = {}
    for node in block.iter():
        if _local_name(node) != "ipsec-security-associations":
            continue
        parsed = _parse_direction(node)
        direction = parsed.get("direction") or f"unknown-{len(directions) + 1}"
        directions[direction] = parsed

    events = []
    for node in block.iter():
        if _local_name(node) != "sa-ipsec-tunnel-event":
            continue
        events.append({
            "time": _first_text(node, "sa-tunnel-event-time"),
            "description": _first_text(node, "sa-tunnel-event-description"),
            "count": _number(_first_text(node, "sa-tunnel-event-num-times")),
        })

    return {
        "tunnel_index": _first_text(
            block,
            "sa-tunnel-index",
            default=str(discovered_index),
        ),
        "block_state": _first_text(block, "sa-block-state"),
        "up": 1 if _first_text(block, "sa-block-state").lower() == "up" else 0,
        "logical_system": _first_text(block, "sa-virtual-system"),
        "vpn_name": _first_text(block, "sa-vpn-name"),
        "local_gateway": _first_text(block, "sa-local-gateway"),
        "remote_gateway": _first_text(block, "sa-remote-gateway"),
        "traffic_selector_name": _first_text(block, "sa-traffic-selector-name"),
        "local_identity": _first_text(block, "sa-local-identity"),
        "remote_identity": _first_text(block, "sa-remote-identity"),
        "traffic_selector_type": _first_text(block, "sa-ts-type"),
        "ike_version": _first_text(block, "sa-ike-version"),
        "quantum_secured": _first_text(block, "sa-is-quantum-secured"),
        "pfs_group": _first_text(block, "sa-pfs-group"),
        "encapsulation_protocol": _first_text(
            block,
            "sa-packet-encapsulation-protocol",
        ),
        "encapsulation_destination_port": _number(
            _first_text(block, "sa-packet-encapsulation-destination-port")
        ),
        "srg_id": _number(_first_text(block, "sa-srg-id")),
        "passive_mode_tunneling": _first_text(block, "sa-passive-mode-tunneling"),
        "df_bit": _first_text(block, "sa-df-bit"),
        "copy_outer_dscp": _first_text(block, "sa-copy-outer-dscp"),
        "policy_name": _first_text(block, "sa-policy-name"),
        "bind_interface": _first_text(block, "sa-bind-interface"),
        "port": _number(_first_text(block, "sa-port")),
        "negotiations_total": _number(_first_text(block, "sa-nego-num")),
        "negotiation_failures_total": _number(_first_text(block, "sa-nego-fail")),
        "deletions_total": _number(_first_text(block, "sa-del-num")),
        "flag": _number(_first_text(block, "sa-flag")),
        "fpc": _number(_first_text(block, "sa-fpc")),
        "pic": _number(_first_text(block, "sa-pic")),
        "anchor_thread": _number(_first_text(block, "sa-anchor-thread")),
        "distribution_key": _first_text(block, "sa-tunnel-dist-key"),
        "event_count": len(events),
        "last_event_time": events[0]["time"] if events else "",
        "last_event_description": events[0]["description"] if events else "",
        "last_event_repeat_count": events[0]["count"] if events else 0,
        "directions": directions,
    }


def collect_ipsec_security_associations_detail(client):
    indices = _summary_indices(client)
    tunnels = {}
    query_failures = 0

    for tunnel_index in indices:
        try:
            reply = client.conn.dispatch(_detail_rpc(tunnel_index))
            detail = _parse_detail(_reply_root(reply), tunnel_index)
            tunnels[str(tunnel_index)] = detail
        except Exception:
            query_failures += 1

    return {
        "name": "ipsec_security_associations_detail",
        "metrics": {
            "discovered_total": len(indices),
            "collected_total": len(tunnels),
            "query_failures_total": query_failures,
            "tunnels": tunnels,
        },
    }
