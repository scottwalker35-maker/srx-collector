"""
Collector: IKE Security Association Detail

Junos CLI:
    show security ike security-associations detail index <ike-index>

XML RPC:
    <get-ike-security-associations-information>
        <detail/>
        <show-index-ike-security-association>INDEX</show-index-ike-security-association>
    </get-ike-security-associations-information>

Discovery RPC:
    <get-ike-security-associations-information/>

The summary RPC dynamically discovers every current IKE index. This collector
then requests detail for each discovered index. The IKE index is used for
current-state correlation and is not treated as a permanent VPN identity.
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
        if _local_name(element) not in wanted:
            continue
        if element.text is None:
            continue
        value = str(element.text).strip()
        if value:
            return value
    return default


def _all_text(root, *names):
    wanted = set(names)
    values = []
    for element in root.iter():
        if _local_name(element) not in wanted:
            continue
        if element.text is None:
            continue
        value = str(element.text).strip()
        if value and value not in values:
            values.append(value)
    return values


def _number(value, default=0):
    if value is None:
        return default
    text = str(value).strip().replace(",", "")
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return default
    number = float(match.group(0))
    return int(number) if number.is_integer() else number


def _remaining_lifetime_seconds(root):
    direct = _first_text(
        root,
        "ike-sa-lifetime",
        "ike-sa-remaining-lifetime",
        "remaining-lifetime",
        "lifetime-remaining",
    )
    if direct:
        return _number(direct)

    expiry = _first_text(
        root,
        "ike-sa-expiration-time",
        "ike-sa-expiry",
        "ike-sa-expire-time",
    )
    return _number(expiry)


def _summary_indices(client):
    reply = client.conn.dispatch(
        etree.XML("<get-ike-security-associations-information/>")
    )
    root = _reply_root(reply)
    indices = []

    for element in root.iter():
        if _local_name(element) != "ike-sa-index":
            continue
        if element.text is None:
            continue
        value = str(element.text).strip()
        if value and value not in indices:
            indices.append(value)

    return indices


def _detail_rpc(ike_index):
    rpc = etree.Element("get-ike-security-associations-information")
    etree.SubElement(rpc, "detail")
    index_node = etree.SubElement(
        rpc,
        "show-index-ike-security-association",
    )
    index_node.text = str(ike_index)
    return rpc


def _parse_detail(root, discovered_index):
    ike_index = _first_text(
        root,
        "ike-sa-index",
        default=str(discovered_index),
    )
    state = _first_text(root, "ike-sa-state")

    associated_tunnel_ids = _all_text(
        root,
        "ike-sa-tunnel-id",
        "ipsec-sa-tunnel-index",
        "tunnel-index",
        "ike-sa-associated-tunnel-id",
    )

    return {
        "ike_index": ike_index,
        "state": state,
        "up": 1 if state.upper() == "UP" else 0,
        "gateway": _first_text(
            root,
            "ike-sa-gateway-name",
            "ike-gateway-name",
            "gateway-name",
        ),
        "local_address": _first_text(
            root,
            "ike-sa-local-address",
            "local-address",
        ),
        "remote_address": _first_text(
            root,
            "ike-sa-remote-address",
            "remote-address",
        ),
        "ike_version": _first_text(root, "ike-sa-version", "ike-version"),
        "exchange_type": _first_text(
            root,
            "ike-sa-exchange-type",
            "exchange-type",
        ),
        "authentication_method": _first_text(
            root,
            "ike-sa-authentication-method",
            "authentication-method",
        ),
        "encryption_algorithm": _first_text(
            root,
            "ike-sa-encryption-algorithm",
            "encryption-algorithm",
        ),
        "authentication_algorithm": _first_text(
            root,
            "ike-sa-authentication-algorithm",
            "authentication-algorithm",
        ),
        "prf_algorithm": _first_text(
            root,
            "ike-sa-prf-algorithm",
            "prf-algorithm",
        ),
        "dh_group": _first_text(root, "ike-sa-dh-group", "dh-group"),
        "remaining_lifetime_seconds": _remaining_lifetime_seconds(root),
        "packets_in": _number(
            _first_text(
                root,
                "ike-sa-packets-in",
                "ike-sa-input-packets",
                "input-packets",
            )
        ),
        "packets_out": _number(
            _first_text(
                root,
                "ike-sa-packets-out",
                "ike-sa-output-packets",
                "output-packets",
            )
        ),
        "bytes_in": _number(
            _first_text(
                root,
                "ike-sa-bytes-in",
                "ike-sa-input-bytes",
                "input-bytes",
            )
        ),
        "bytes_out": _number(
            _first_text(
                root,
                "ike-sa-bytes-out",
                "ike-sa-output-bytes",
                "output-bytes",
            )
        ),
        "ipsec_sa_created": _number(
            _first_text(
                root,
                "ike-sa-ipsec-sa-created",
                "ipsec-sa-created",
                "ipsec-sas-created",
            )
        ),
        "ipsec_sa_deleted": _number(
            _first_text(
                root,
                "ike-sa-ipsec-sa-deleted",
                "ipsec-sa-deleted",
                "ipsec-sas-deleted",
            )
        ),
        "phase2_negotiations": _number(
            _first_text(
                root,
                "ike-sa-phase2-negotiations",
                "phase2-negotiations",
            )
        ),
        "phase2_failures": _number(
            _first_text(
                root,
                "ike-sa-phase2-failures",
                "phase2-failures",
                "failed-phase2-negotiations",
            )
        ),
        "rekey_count": _number(
            _first_text(
                root,
                "ike-sa-rekey-count",
                "rekey-count",
                "rekeys",
            )
        ),
        "associated_tunnel_count": len(associated_tunnel_ids),
        "associated_tunnel_ids": ",".join(associated_tunnel_ids),
    }


def collect_ike_security_associations_detail(client):
    indices = _summary_indices(client)
    associations = {}
    query_failures = 0

    for ike_index in indices:
        try:
            reply = client.conn.dispatch(_detail_rpc(ike_index))
            detail_root = _reply_root(reply)
            associations[str(ike_index)] = _parse_detail(
                detail_root,
                ike_index,
            )
        except Exception:
            query_failures += 1

    return {
        "name": "ike_security_associations_detail",
        "metrics": {
            "discovered_total": len(indices),
            "collected_total": len(associations),
            "query_failures_total": query_failures,
            "associations": associations,
        },
    }
