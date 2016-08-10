#!/usr/bin/env python2
# coding=UTF-8
import os, time, logging, sys, json, random

sys.path.append(os.path.dirname(__file__))
from mininet import net
from mininet.cli import CLI

from utils import Floodlight
from resources import emu_config
from overlord.Overlord import Overlord
from utils.MiscUtils import addHostToMininet, mkdir_p
from utils.TcptraceParser import TcptraceParser

pypath = "PYTHONPATH=$PYTHONPATH:%s "%emu_config.basedir

if __name__ == '__main__':
    logging.basicConfig(**emu_config.logging_config)

    net = net.Mininet(controller=Floodlight.Controller)
    net.addController("controller1")
    switch = net.addSwitch("switch1")
    overlord = Overlord()

    hosts = []
    for i in range(1, 6):
        current_host = addHostToMininet(net, switch, "host%d"%i, overlord, bw=25)
        hosts.append(current_host)
    victim = addHostToMininet(net, switch, "victim1", overlord, bw=90)
    sensor = addHostToMininet(net, switch, "sensor1", overlord)

    net.start()
    # net.pingAll()

    for node in hosts + [victim, sensor]:
        node.cmd(pypath + " python2 overlord/Host.py %s &"%node.name)
    time.sleep(5)

    overlord.startRunnable("TestWebsite", "TestWebsite", hostlist=[victim.name])
    overlord.startRunnable("Sensor", "Sensor", {"pagesToWatch": ["http://%s/?root=432"%victim.IP()]},
                           hostlist=[sensor.name])
    for h in hosts:
        current_peerlist = [random.sample([x.IP() for x in hosts if not x == h], 2)]
        overlord.startRunnable("overbot.KademliaBot", "KademliaBot", {"name": h.name,
                                                              "peerlist"    : current_peerlist}, hostlist=[h.name])
    pcapfile = "/tmp/botnetemulator/tcptrace/victim.pcap"
    mkdir_p(os.path.dirname(pcapfile))
    victim.cmd("tshark -F pcap -w %s port http or port https &"%pcapfile)
    logging.debug("Runnables wurden gestartet")
    time.sleep(25)

    chosenOne = random.choice(hosts)
    result = chosenOne.cmd("curl -X POST --data 'command=ddos_server&kwargs=%s' '%s'"
                           %(json.dumps({"url": "http://%s:%d/ddos_me"%(victim.IP(), emu_config.PORT)}),
                             "http://%s:%d/current_command"%(chosenOne.IP(), emu_config.PORT)), verbose=True)
    logging.debug("curl: %s"%result)
    time.sleep(25)
    overlord.desinfectRandomBots(0.3, [h.name for h in hosts])
    time.sleep(15)
    overlord.desinfectRandomBots(0.2, [h.name for h in hosts])
    time.sleep(15)
    overlord.desinfectRandomBots(1, [h.name for h in hosts])
    time.sleep(25)

    # CLI(net)
    print "tshark: ", victim.cmd("jobs")
    overlord.stopEverything()
    net.stop()

    ttparser = TcptraceParser(host="victim")
    stats = ttparser.extractConnectionStatisticsFromPcap(pcapfile)
