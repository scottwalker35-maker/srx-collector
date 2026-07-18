"""
Collector: Security Policy Hit Counts

CLI:
    show security policies hit-count

RPC:
    get-security-policies-hit-count

Every policy returned by Junos is collected dynamically. Newly created
policies appear automatically on the next successful collection cycle.
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


def _text(element, path, default=""):
    value = element.findtext(path)
    return default if value is None else str(value).strip()


def _integer(value):
    value = str(value or "").strip().replace(",", "")
    if value == "":
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def collect_security_policy_hit_count(client):
    rpc = etree.Element("get-security-policies-hit-count")
    root = _reply_root(client.conn.dispatch(rpc))

    logical_system = (
        root.findtext(".//logical-system-name")
        or "root-logical-system"
    ).strip()

    policies = {}

    for entry in root.findall(".//policy-hit-count-entry"):
        policy_name = _text(entry, "policy-hit-count-policy-name")
        from_zone = _text(entry, "policy-hit-count-from-zone")
        to_zone = _text(entry, "policy-hit-count-to-zone")
        action = _text(entry, "policy-hit-count-action")
        index = _integer(_text(entry, "policy-hit-count-index", "0"))
        hit_count = _integer(_text(entry, "policy-hit-count-count", "0"))

        entry_key = f"{logical_system}|{from_zone}|{to_zone}|{policy_name}"
        policies[entry_key] = {
            "logical_system": logical_system,
            "from_zone": from_zone,
            "to_zone": to_zone,
            "policy": policy_name,
            "action": action,
            "index": index,
            "hit_count_total": hit_count,
        }

    return {
        "name": "security_policy_hit_count",
        "metrics": policies,
    }
