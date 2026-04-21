"""
firewall.py - SDN Firewall for POX Controller
Place this file in ~/pox/ext/firewall.py

Start with:
  cd ~/pox
  python3 pox.py log.level --DEBUG forwarding.l2_learning firewall

How it works:
  - Builds on top of POX's built-in l2_learning (handles MAC learning
    and normal forwarding automatically)
  - This component only intercepts PacketIn events and checks the
    source/destination IP against a rule table
  - If blocked: installs a DROP flow entry on the switch
  - If allowed: does nothing (l2_learning handles the forwarding)

Rule table (edit RULES below to change):
  Each rule is a dict with:
    src  - source IP to match      (* = any)
    dst  - destination IP to match (* = any)
    action - 'block' or 'allow'

Default policy: ALLOW anything not explicitly listed.
"""

from pox.core import core
from pox.lib.packet import ethernet, ipv4
from pox.lib.addresses import IPAddr
import pox.openflow.libopenflow_01 as of

log = core.getLogger()

# ----------------------------------------------------------------
# FIREWALL RULES — edit these to change behaviour
# Format: src IP, dst IP, action
# Use '*' to mean "any IP"
# Rules are checked top to bottom; first match wins
# ----------------------------------------------------------------
RULES = [
    {'src': '10.0.0.1', 'dst': '10.0.0.3', 'action': 'block'},  # h1 cannot reach h3
    {'src': '10.0.0.3', 'dst': '10.0.0.1', 'action': 'block'},  # h3 cannot reach h1
    {'src': '*',        'dst': '*',         'action': 'allow'},  # everything else allowed
]


def _check_rules(src_ip, dst_ip):
    """
    Walk the rule table top to bottom.
    Return 'block' or 'allow' for the given src/dst IP pair.
    """
    for rule in RULES:
        src_match = (rule['src'] == '*' or rule['src'] == str(src_ip))
        dst_match = (rule['dst'] == '*' or rule['dst'] == str(dst_ip))
        if src_match and dst_match:
            return rule['action']
    return 'allow'   # default policy


def _install_drop(event, src_ip, dst_ip):
    """
    Push a DROP flow entry to the switch for this src/dst IP pair.
    idle_timeout=30  — entry removed after 30s of no matching traffic
    hard_timeout=120 — entry removed after 120s regardless
    """
    msg = of.ofp_flow_mod()
    msg.match.dl_type = ethernet.IP_TYPE
    msg.match.nw_src  = IPAddr(src_ip)
    msg.match.nw_dst  = IPAddr(dst_ip)
    msg.idle_timeout  = 30
    msg.hard_timeout  = 120
    msg.priority      = 100          # higher than l2_learning entries
    # Empty action list = DROP
    event.connection.send(msg)
    log.warning('BLOCKED  %s -> %s  (drop flow installed)', src_ip, dst_ip)


class Firewall(object):
    """
    POX component that enforces IP-based firewall rules.
    Registered as a listener on PacketIn events from every switch.
    """

    def __init__(self):
        core.openflow.addListeners(self)
        log.info('Firewall component started')
        log.info('Rules loaded:')
        for i, r in enumerate(RULES):
            log.info('  Rule %d: src=%-15s dst=%-15s action=%s',
                     i + 1, r['src'], r['dst'], r['action'].upper())

    def _handle_PacketIn(self, event):
        packet = event.parsed
        if not packet.parsed:
            return

        # Only care about IP packets
        ip_pkt = packet.find('ipv4')
        if ip_pkt is None:
            return   # ARP, LLDP etc — let l2_learning handle them

        src_ip = ip_pkt.srcip
        dst_ip = ip_pkt.dstip
        action = _check_rules(src_ip, dst_ip)

        if action == 'block':
            _install_drop(event, src_ip, dst_ip)
            # Drop this specific packet too (don't forward it)
            return

        # action == 'allow' — log and let l2_learning forward it
        log.debug('ALLOWED  %s -> %s', src_ip, dst_ip)


def launch():
    """
    POX entry point — called when the component is loaded.
    """
    core.registerNew(Firewall)
