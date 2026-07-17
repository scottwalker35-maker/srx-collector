from ncclient import manager

HOST = "192.168.68.98"
PORT = 830
USERNAME = "walkersc"
PASSWORD = "walks634"

with manager.connect(
    host=HOST,
    port=PORT,
    username=USERNAME,
    password=PASSWORD,
    hostkey_verify=False,
    device_params={"name": "junos"},
    allow_agent=False,
    look_for_keys=False,
) as m:

    print("Connected!")
    print("Server Capabilities:")

    for cap in m.server_capabilities:
        print(cap)
