"""
Collector: IKE Security Association Summary

CLI:
    show security ike security-associations

RPC:
    <get-ike-security-associations-information/>

Repeating XML entry:
    ike-security-associations

All returned IKE SAs are discovered dynamically. The IKE index is exported
for current-state correlation, but is not treated as a permanent identity.
"""

from lxml import etree


def _reply_root(reply):
    if hasattr(reply, "xml"):
        return etree.fromstring(reply.xml.encode())
    if hasattr(reply, "data_xml"):
        return etree.fromstring(reply.data_xml.encode())
    if hasattr(reply, "_NCElement__doc"):
        return reply._NCElement__doc.getroot()
    raise RuntimeError(
        f"Unsupported ncclient reply type: {type(reply)}"
    )


def _text(node, path, default=""):
    value = node.findtext(path)
    return default if value is None else str(value).strip()


def collect_ike_security_associations(client):
    rpc = etree.XML(
        "<get-ike-security-associations-information/>"
    )
    root = _reply_root(client.conn.dispatch(rpc))
    associations = {}

    for node in root.findall(".//ike-security-associations"):
        ike_index = _text(node, "ike-sa-index")
        if not ike_index:
            continue

        state = _text(node, "ike-sa-state")
        associations[ike_index] = {
            "ike_index": ike_index,
            "state": state,
            "up": 1 if state.upper() == "UP" else 0,
            "remote_address": _text(
                node,
                "ike-sa-remote-address",
            ),
            "exchange_type": _text(
                node,
                "ike-sa-exchange-type",
            ),
        }

    up_total = sum(
        item["up"] for item in associations.values()
    )

    return {
        "name": "ike_security_associations",
        "metrics": {
            "sa_total": len(associations),
            "sa_up_total": up_total,
            "sa_down_total": len(associations) - up_total,
            "associations": associations,
        },
    }
