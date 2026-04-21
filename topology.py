"""
topology.py - Mininet topology for SDN Firewall demo

Topology:
    h1 (10.0.0.1)
    h2 (10.0.0.2)  --- s1 --- POX controller (127.0.0.1:6633)
    h3 (10.0.0.3)

Usage:
    sudo python3 topology.py

Start POX first in another terminal:
    cd ~/pox
    python3 pox.py log.level --DEBUG forwarding.l2_learning firewall
"""

from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info


def build():
    net = Mininet(
        controller=RemoteController,
        switch=OVSKernelSwitch,
        autoSetMacs=True
    )

    info('*** Adding controller\n')
    net.addController('c0',
                      controller=RemoteController,
                      ip='127.0.0.1',
                      port=6633)

    info('*** Adding switch\n')
    s1 = net.addSwitch('s1')

    info('*** Adding hosts\n')
    h1 = net.addHost('h1', ip='10.0.0.1/24')
    h2 = net.addHost('h2', ip='10.0.0.2/24')
    h3 = net.addHost('h3', ip='10.0.0.3/24')

    info('*** Adding links\n')
    net.addLink(h1, s1)
    net.addLink(h2, s1)
    net.addLink(h3, s1)

    info('*** Starting network\n')
    net.build()
    net.controllers[0].start()
    s1.start([net.controllers[0]])

    info('\n*** Hosts: h1=10.0.0.1  h2=10.0.0.2  h3=10.0.0.3\n')
    info('*** Firewall rules: h1<->h3 BLOCKED, everything else ALLOWED\n\n')

    CLI(net)

    info('*** Stopping network\n')
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    build()
