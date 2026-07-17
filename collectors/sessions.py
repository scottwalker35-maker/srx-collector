"""
Collector: Session Summary

CLI:
    show security flow session summary

RPC:
    get-flow-session-information

Metrics:
    - active_unicast_sessions
    - active_multicast_sessions
    - active_services_offload_sessions
    - failed_sessions
    - active_drop_sessions
    - active_sessions
    - active_session_valid
    - active_session_pending
    - active_session_invalidated
    - active_session_other
    - max_sessions
"""

from lxml import etree


def collect_sessions(client):

    rpc = etree.XML("""
    <get-flow-session-information>
        <summary/>
    </get-flow-session-information>
    """)

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
        "name": "sessions",
        "metrics": {
            "active_unicast_sessions":
                root.findtext(".//active-unicast-sessions"),
            "active_multicast_sessions":
                root.findtext(".//active-multicast-sessions"),
            "active_services_offload_sessions":
                root.findtext(".//active-services-offload-sessions"),
            "failed_sessions":
                root.findtext(".//failed-sessions"),
            "active_drop_sessions":
                root.findtext(".//active-drop-sessions"),
            "active_sessions":
                root.findtext(".//active-sessions"),
            "active_session_valid":
                root.findtext(".//active-session-valid"),
            "active_session_pending":
                root.findtext(".//active-session-pending"),
            "active_session_invalidated":
                root.findtext(".//active-session-invalidated"),
            "active_session_other":
                root.findtext(".//active-session-other"),
            "max_sessions":
                root.findtext(".//max-sessions"),
        },
    }
