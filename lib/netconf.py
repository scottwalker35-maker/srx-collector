"""
NETCONF Client

Handles all communication with Juniper devices.

Responsibilities
----------------
- Connect to NETCONF
- Disconnect
- Execute RPCs
- Always return an lxml root element
"""

from lxml import etree
from ncclient import manager


class NetconfClient:

    def __init__(self, host, port, username, password):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.conn = None

    def connect(self):

        self.conn = manager.connect(
            host=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
            hostkey_verify=False,
            device_params={"name": "junos"},
            allow_agent=False,
            look_for_keys=False,
            timeout=30,
        )

    def disconnect(self):

        if self.conn:
            self.conn.close_session()

    def rpc(self, rpc_name):
        """
        Execute an RPC and always return an lxml root element.
        """

        xml = etree.XML(f"<{rpc_name}/>")

        reply = self.conn.dispatch(xml)

        #
        # ncclient has changed over the years.
        # Handle every version we've seen.
        #

        if hasattr(reply, "xml"):
            return etree.fromstring(reply.xml.encode())

        if hasattr(reply, "data_xml"):
            return etree.fromstring(reply.data_xml.encode())

        if hasattr(reply, "_NCElement__doc"):
            return reply._NCElement__doc.getroot()

        raise RuntimeError(
            f"Unsupported ncclient reply type: {type(reply)}"
        )
