from lxml import etree


def rpc(conn, rpc_name):
    xml = etree.XML(f"<{rpc_name}/>")
    return conn.dispatch(xml)


def get_root(reply):
    """
    Convert the returned ncclient object into an lxml Element.
    Works with older and newer ncclient versions.
    """

    if hasattr(reply, "xml"):
        return etree.fromstring(reply.xml.encode())

    if hasattr(reply, "data_xml"):
        return etree.fromstring(reply.data_xml.encode())

    if hasattr(reply, "_NCElement__doc"):
        return reply._NCElement__doc.getroot()

    raise Exception(f"Unsupported reply type: {type(reply)}")


def get_system_information(conn):

    reply = rpc(conn, "get-system-information")
    root = get_root(reply)

    return {
        "hostname": root.findtext(".//host-name"),
        "model": root.findtext(".//hardware-model"),
        "family": root.findtext(".//os-name"),
        "version": root.findtext(".//os-version"),
        "serial": root.findtext(".//serial-number"),
    }


def get_ha_information(conn):

    reply = rpc(conn, "get-chassis-high-availability-information")
    root = get_root(reply)

    return {
        "node_status": root.findtext(".//node-status"),
        "role": root.findtext(".//node-role"),
        "peer_role": root.findtext(".//peer-node-role"),
        "health": root.findtext(".//health-status"),
        "readiness": root.findtext(".//failover-readiness"),
        "peer_bfd": root.findtext(".//high-availability-peer-bfd-status"),
    }
