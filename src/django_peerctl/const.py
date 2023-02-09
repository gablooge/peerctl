from django.utils.translation import gettext as _
from django.conf import settings

from django_peerctl.confutil import discover_netom_templates

DEVICE_TYPES = (
    ("arista", "Arista EOS"),
    ("bird", "BIRD"),
    ("bird2", "BIRD 2"),
    ("cisco", "Cisco IOS"),
    ("cisco-xr", "Cisco IOS XR"),
    ("cisco-nexus", "Cisco Nexus"),
    ("junos", "Juniper Junos OS"),
    ("junos-set", "Juniper Junos OS set"),
    ("sros-md", "Nokia SR OS MD-CLI"),
    ("sros-classic", "Nokia SR OS Classic CLI"),
)

NET_TYPES = (
    ("NSP", _("NSP")),
    ("Content", _("Content")),
    ("Cable/DSL/ISP", _("Cable/DSL/ISP")),
    ("Enterprise", _("Enterprise")),
    ("Educational/Research", _("Educational/Research")),
    ("Non-Profit", _("Non-Profit")),
    ("Route Server", _("Route Server")),
    ("Network Services", _("Network Services")),
    ("Route Collector", _("Route Collector")),
    ("Government", _("Government")),
)

DEVICE_TEMPLATES, DEVICE_TEMPLATE_TYPES = discover_netom_templates(
    DEVICE_TYPES, settings.NETOM_TEMPLATE_DIR
)

AUDIT_EVENTS = (
    ("peer_session-request", "Peering Request"),
    ("peer_session-add", "Session Add"),
    ("peer_session-del", "Session Delete"),
    ("peer_session-mod", "Session Modify"),
    ("policy-mod", "Policy Modify"),
    ("email", "Email"),
)

EMAIL_ORIGIN = (
    ("peer_session-workflow", "Peering Session Workflow"),
    ("bulk-email", "Notification Email"),
)
