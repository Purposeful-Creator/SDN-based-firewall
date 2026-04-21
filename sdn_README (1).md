# SDN-Based Firewall

A Software-Defined Networking firewall built with **POX controller** and **Mininet**, implementing IP-based traffic filtering using OpenFlow 1.0.

---

## Repository

[github.com/Purposeful-Creator/SDN-based-firewall](https://github.com/Purposeful-Creator/SDN-based-firewall)

---

## Project Overview

This project implements a network firewall at the **control plane** rather than at individual endpoints. A centralised POX controller makes all packet filtering decisions. An Open vSwitch (OVS) enforces those decisions at line rate without re-involving the controller after the first packet of each flow.

The key SDN principle demonstrated: **separation of the control plane from the data plane**. The controller (POX + `firewall.py`) is the brain. The switch (OVS) is the muscle. They communicate over OpenFlow.

---

## Architecture

```
h1 (10.0.0.1) ─┐
h2 (10.0.0.2) ──── s1 (OVS) ══ OpenFlow 1.0 ══ POX Controller
h3 (10.0.0.3) ─┘                                    │
                                              firewall.py
                                              l2_learning
```

Three hosts connect to one OpenFlow switch. The switch has no built-in logic — it asks the controller what to do with every new flow it encounters.

---

## Files

| File | Purpose |
|------|---------|
| `firewall.py` | POX controller component — firewall rule engine |
| `topology.py` | Mininet topology — 3 hosts, 1 OVS switch |
| `test.py` | Verification test sequence |

---

## How It Works

### OpenFlow handshake

When Mininet starts the switch and points it at the POX controller:

1. OVS opens a TCP connection to `127.0.0.1:6633`
2. Both sides exchange `OFPT_HELLO` to agree on OpenFlow version
3. POX sends `OFPT_FEATURES_REQUEST`; OVS replies with its datapath ID and capabilities
4. POX installs a **table-miss entry** (priority 0, match-all, action: send to controller)

From this point, every packet the switch does not recognise is sent up to POX as a `PacketIn` event.

### Packet-In decision pipeline

```
New packet arrives at s1
        │
        ▼
No matching flow entry → Packet-In to POX
        │
        ▼
firewall._handle_PacketIn()
        │
        ├── Extract src IP, dst IP from IPv4 header
        │
        ├── Walk RULES list top-to-bottom (first match wins)
        │
        ├── BLOCK → push DROP flow entry to switch
        │           (priority 100, empty action list)
        │           future packets dropped at wire speed
        │
        └── ALLOW → l2_learning installs forwarding entry
                    packet forwarded normally
```

The first packet of a blocked flow reaches the controller once. After that, the DROP entry in the switch handles all subsequent packets without controller involvement.

### Firewall rule table

Rules are defined at the top of `firewall.py`:

```python
RULES = [
    {'src': '10.0.0.1', 'dst': '10.0.0.3', 'action': 'block'},
    {'src': '10.0.0.3', 'dst': '10.0.0.1', 'action': 'block'},
    {'src': '*',        'dst': '*',         'action': 'allow'},
]
```

- Matching is top-to-bottom; first match wins
- `*` means any IP address
- Default policy: allow (the catch-all rule at the bottom)

### Flow entry installed on block

```
Priority:     100
Match:        ip_src = <src>, ip_dst = <dst>
Action:       (empty — DROP)
idle_timeout: 30 seconds
hard_timeout: 120 seconds
```

Flow entries expire automatically, keeping the switch flow table clean.

---

## Setup

### Prerequisites

```bash
sudo apt update
sudo apt install -y mininet openvswitch-switch python3-pip
pip3 install pox
sudo service openvswitch-switch start
```

### File placement

```bash
cp firewall.py ~/pox/ext/firewall.py
```

---

## Running the Project

**Terminal 1 — start POX controller first:**

```bash
cd ~/pox
python3 pox.py log.level --DEBUG forwarding.l2_learning firewall
```

Wait until you see:
```
INFO:firewall:Firewall component started
```

**Terminal 2 — start Mininet topology:**

```bash
sudo python3 topology.py
```

---

## Demo Commands

Run inside the `mininet>` prompt:

```bash
# Should succeed — h1 to h2 is allowed
mininet> h1 ping -c2 h2

# Should fail — h1 to h3 is blocked (100% packet loss)
mininet> h1 ping -c2 h3

# Should fail — h3 to h1 is blocked
mininet> h3 ping -c2 h1

# Should succeed — h2 to h3 is allowed
mininet> h2 ping -c2 h3
```

---

## Verification Screenshots

### POX controller terminal

When `h1 ping h3` is run, the controller logs:

```
WARNING:firewall:BLOCKED  10.0.0.1 -> 10.0.0.3  (drop flow installed)
WARNING:firewall:BLOCKED  10.0.0.3 -> 10.0.0.1  (drop flow installed)
```

When `h1 ping h2` is run:

```
DEBUG:firewall:ALLOWED   10.0.0.1 -> 10.0.0.2
```

### Mininet terminal

Blocked path shows `100% packet loss`. Allowed paths show `0% packet loss` with normal round-trip times.

---

## Shutdown

```bash
# In Mininet terminal
mininet> exit
sudo mn -c

# In POX terminal
Ctrl + C
```

---

## Design Decisions

| Decision | Choice | Justification |
|----------|--------|---------------|
| Controller | POX | Lightweight, Python-based, easy to extend |
| Default policy | Fail-open (allow) | Safer for demonstrations; production would use fail-closed |
| Rule matching | First-match, top-to-bottom | Predictable and easy to reason about |
| Flow timeouts | idle=30s, hard=120s | Stale entries auto-expire; avoids flow table bloat |
| Co-loading l2_learning | Yes | Handles MAC learning and normal forwarding automatically; firewall only needs to handle the block decision |

---

## Firewall vs Traditional Approach

| | Traditional (host-based) | This project (SDN) |
|--|--------------------------|-------------------|
| Where enforced | At each endpoint | At the switch |
| Who decides | Each host independently | One centralised controller |
| Policy update | Change config on every host | Change one rule list in controller |
| Bypass risk | Attacker can disable on compromised host | Enforcement is at the network layer |

---

## Concepts Demonstrated

- OpenFlow Packet-In / Flow-Mod message exchange
- Table-miss entry and controller-driven forwarding
- Flow entry priority and timeout management
- Separation of control plane and data plane
- First-match rule semantics
- Co-existence of multiple POX components on the same event stream
