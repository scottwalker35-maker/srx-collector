"""
Collector: Security Screen Statistics

CLI:
    show security screen statistics zone <zone>

RPC:
    get-ids-statistics
"""

from lxml import etree


_XML_TO_METRIC = {
    "ids-statistics-icmp-flood": "icmp_flood_total",
    "ids-statistics-udp-flood": "udp_flood_total",
    "ids-statistics-winnuke": "tcp_winnuke_total",
    "ids-statistics-tcp-port-scan": "tcp_port_scan_total",
    "ids-statistics-udp-port-scan": "udp_port_scan_total",
    "ids-statistics-address-sweep": "icmp_address_sweep_total",
    "ids-statistics-tcp-sweep": "tcp_sweep_total",
    "ids-statistics-udp-sweep": "udp_sweep_total",
    "ids-statistics-tear-drop": "ip_tear_drop_total",
    "ids-statistics-syn-flood": "tcp_syn_flood_total",
    "ids-statistics-syn-flood-src": "tcp_syn_flood_source_total",
    "ids-statistics-syn-flood-dst": "tcp_syn_flood_destination_total",
    "ids-statistics-ip-spoofing": "ip_spoofing_total",
    "ids-statistics-ping-of-death": "icmp_ping_of_death_total",
    "ids-statistics-ip-option-src-route": "ip_source_route_option_total",
    "ids-statistics-land": "tcp_land_total",
    "ids-statistics-syn-fragment": "tcp_syn_fragment_total",
    "ids-statistics-tcp-no-flag": "tcp_no_flag_total",
    "ids-statistics-unknown-protocol": "ip_unknown_protocol_total",
    "ids-statistics-ip-option-bad": "ip_bad_options_total",
    "ids-statistics-ip-option-record-route": "ip_record_route_option_total",
    "ids-statistics-ip-option-timestamp": "ip_timestamp_option_total",
    "ids-statistics-ip-option-security": "ip_security_option_total",
    "ids-statistics-ip-option-loose-src-route": "ip_loose_source_route_option_total",
    "ids-statistics-ip-option-strict-src-route": "ip_strict_source_route_option_total",
    "ids-statistics-ip-option-stream": "ip_stream_option_total",
    "ids-statistics-icmp-fragment": "icmp_fragment_total",
    "ids-statistics-icmp-large-pkt": "icmp_large_packet_total",
    "ids-statistics-syn-fin": "tcp_syn_fin_total",
    "ids-statistics-fin-no-ack": "tcp_fin_no_ack_total",
    "ids-statistics-src-session-limit": "source_session_limit_total",
    "ids-statistics-syn-ack-ack-proxy": "tcp_syn_ack_ack_proxy_total",
    "ids-statistics-block-fragment": "ip_block_fragment_total",
    "ids-statistics-dst-session-limit": "destination_session_limit_total",
    "ids-statistics-ipv6-ext-header": "ipv6_extension_header_total",
    "ids-statistics-ipv6-ext-hbyh-option": "ipv6_extension_hop_by_hop_option_total",
    "ids-statistics-ipv6-ext-dst-option": "ipv6_extension_destination_option_total",
    "ids-statistics-ipv6-ext-header-limit": "ipv6_extension_header_limit_total",
    "ids-statistics-ipv6-malformed-header": "ipv6_malformed_header_total",
    "ids-statistics-icmpv6-malformed-packet": "icmpv6_malformed_packet_total",
    "ids-statistics-ip-tunnel-summary": "ip_tunnel_summary_total",
}


def _reply_root(reply):
    if hasattr(reply, "xml"):
        return etree.fromstring(reply.xml.encode())
    if hasattr(reply, "data_xml"):
        return etree.fromstring(reply.data_xml.encode())
    if hasattr(reply, "_NCElement__doc"):
        return reply._NCElement__doc.getroot()
    raise RuntimeError(f"Unsupported ncclient reply type: {type(reply)}")


def _normalize_zones(zones):
    normalized = []
    for zone in zones or []:
        zone = str(zone).strip()
        if zone and zone not in normalized:
            normalized.append(zone)
    return normalized


def _integer(value):
    if value is None:
        return None
    value = str(value).strip().replace(",", "")
    if value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _collect_zone(client, zone):
    rpc = etree.Element("get-ids-statistics")
    etree.SubElement(rpc, "zone").text = zone
    root = _reply_root(client.conn.dispatch(rpc))
    statistics = root.find(".//ids-statistics")
    if statistics is None:
        return {}

    metrics = {}
    for xml_name, metric_name in _XML_TO_METRIC.items():
        value = _integer(statistics.findtext(xml_name))
        if value is not None:
            metrics[metric_name] = value
    return metrics


def collect_security_screen(client, zones=None):
    metrics = {}
    for zone in _normalize_zones(zones):
        metrics[zone] = _collect_zone(client=client, zone=zone)
    return {"name": "security_screen", "metrics": metrics}
