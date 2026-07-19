"""
Collector: IPsec Security Association Summary

Junos CLI:
    show security ipsec security-associations

XML RPC:
    <get-security-associations-information/>

Each returned IPsec SA/tunnel is discovered dynamically. The tunnel index is
retained for drill-down and detail collection, but is not treated as a
permanent VPN identity.
"""

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


def _first_text(node, *names, default=""):
    wanted = set(names)

    for element in node.iter():
        if _local_name(element) not in wanted:
            continue
        if element.text is None:
            continue

        value = str(element.text).strip()
        if value:
            return value

    return default


def _number(value, default=0):
    if value is None:
        return default

    text = str(value).strip().replace(",", "")
    digits = "".join(character for character in text if character.isdigit())

    if not digits:
        return default

    return int(digits)


def _direction_up(direction):
    return 1 if str(direction).strip().lower() in {"in", "out", "inbound", "outbound"} else 0


def collect_ipsec_security_associations(client):
    rpc = etree.XML("<get-security-associations-information/>")
    reply = client.conn.dispatch(rpc)
    root = _reply_root(reply)

    associations = {}

    # Junos versions use slightly different container names. Match any
    # repeating element that contains a tunnel/index field.
    for node in root.iter():
        tunnel_index = _first_text(
            node,
            "sa-tunnel-index",
            "ipsec-sa-tunnel-index",
            "tunnel-index",
        )

        if not tunnel_index:
            continue

        # Avoid treating higher-level containers as duplicate SAs.
        if tunnel_index in associations:
            continue

        direction = _first_text(
            node,
            "sa-direction",
            "direction",
        )

        remote_gateway = _first_text(
            node,
            "sa-remote-gateway",
            "remote-gateway",
            "ipsec-sa-remote-gateway",
        )

        spi = _first_text(
            node,
            "sa-spi",
            "spi",
            "ipsec-sa-spi",
        )

        encryption_algorithm = _first_text(
            node,
            "sa-encryption-algorithm",
            "encryption-algorithm",
        )

        authentication_algorithm = _first_text(
            node,
            "sa-authentication-algorithm",
            "authentication-algorithm",
            "hmac-algorithm",
        )

        lifetime_seconds = _number(
            _first_text(
                node,
                "sa-lifetime",
                "remaining-lifetime",
                "lifetime",
            )
        )

        port = _first_text(
            node,
            "sa-port",
            "port",
        )

        associations[tunnel_index] = {
            "tunnel_index": tunnel_index,
            "remote_gateway": remote_gateway,
            "spi": spi,
            "encryption_algorithm": encryption_algorithm,
            "authentication_algorithm": authentication_algorithm,
            "remaining_lifetime_seconds": lifetime_seconds,
            "port": port,
            "direction": direction,
            "present": _direction_up(direction),
        }

    return {
        "name": "ipsec_security_associations",
        "metrics": {
            "sa_total": len(associations),
            "associations": associations,
        },
    }
