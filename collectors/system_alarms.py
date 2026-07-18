"""
Collector: System Alarms

CLI:
    show system alarms

RPC:
    get-system-alarm-information

Every active alarm returned by Junos is collected dynamically. Newly
raised alarms appear automatically on the next successful collection
cycle, and cleared alarms simply stop being reported.

XML response structure:

    <alarm-information xmlns="http://xml.juniper.net/junos/.../junos-alarm">
        <alarm-summary>
            <active-alarm-count>3</active-alarm-count>
        </alarm-summary>
        <alarm-detail>
            <alarm-time junos:seconds="...">...</alarm-time>
            <alarm-class>Minor</alarm-class>
            <alarm-description>...</alarm-description>
            <alarm-short-description>...</alarm-short-description>
            <alarm-type>System</alarm-type>
        </alarm-detail>
    </alarm-information>

The alarm-information element carries an explicit default XML namespace,
and the alarm-time "seconds" attribute is namespaced with a prefix whose
URI encodes the running Junos version. Both lookups below match on local
name only, so this collector keeps working across Junos versions without
hardcoding a namespace URI.
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


def _find_local(element, tag):
    matches = element.xpath("./*[local-name()='{}']".format(tag))
    return matches[0] if matches else None


def _findall_local(element, tag):
    return element.xpath(".//*[local-name()='{}']".format(tag))


def _text_local(element, tag, default=""):
    child = _find_local(element, tag)
    if child is None or child.text is None:
        return default
    return str(child.text).strip()


def _attrib_local(element, name, default=None):
    if element is None:
        return default
    for key, value in element.attrib.items():
        local_name = key.split("}")[-1] if "}" in key else key
        if local_name == name:
            return value
    return default


def _integer(value):
    value = str(value or "").strip().replace(",", "")
    if value == "":
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def collect_system_alarms(client):
    rpc = etree.Element("get-system-alarm-information")
    root = _reply_root(client.conn.dispatch(rpc))

    alarm_information = _find_local(root, "alarm-information")

    if alarm_information is None:
        return {
            "name": "system_alarms",
            "metrics": {
                "active_alarm_count": 0,
                "alarms": {},
            },
        }

    alarm_summary = _find_local(alarm_information, "alarm-summary")
    active_alarm_count = _integer(
        _text_local(alarm_summary, "active-alarm-count", "0")
        if alarm_summary is not None
        else "0"
    )

    alarms = {}

    for index, entry in enumerate(
        _findall_local(alarm_information, "alarm-detail")
    ):
        alarm_class = _text_local(entry, "alarm-class")
        alarm_type = _text_local(entry, "alarm-type")
        short_description = _text_local(entry, "alarm-short-description")
        description = _text_local(entry, "alarm-description")

        alarm_time = _find_local(entry, "alarm-time")
        raised_timestamp = _integer(
            _attrib_local(alarm_time, "seconds", "0")
        )

        entry_key = f"{alarm_type}|{alarm_class}|{short_description}|{index}"

        alarms[entry_key] = {
            "alarm_class": alarm_class,
            "alarm_type": alarm_type,
            "alarm_short_description": short_description,
            "alarm_description": description,
            "raised_timestamp_seconds": raised_timestamp,
            "active": 1,
        }

    return {
        "name": "system_alarms",
        "metrics": {
            "active_alarm_count": active_alarm_count,
            "alarms": alarms,
        },
    }
