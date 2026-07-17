from ncclient import manager


class NetconfClient:

    def __init__(self, host, username, password, port=830):

        self.host = host
        self.username = username
        self.password = password
        self.port = port
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
        )

    def disconnect(self):

        if self.conn:
            self.conn.close_session()
