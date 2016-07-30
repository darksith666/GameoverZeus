#!/usr/bin/env python2
# coding=UTF-8
import random, subprocess, logging, shlex

from actors.AbstractBot import Runnable, CommandExecutor
from utils.LogfileParser import writeLogentry


class RandomTrafficReceiver(Runnable):
    """The abstract base class for all clients in the simulated botnets"""

    def __init__(self, peerlist=[], **kwargs):
        super(RandomTrafficReceiver, self).__init__(**kwargs)
        assert isinstance(peerlist, list), "type(current_peerlist): %s"%type(peerlist)

        self.peerlist = peerlist
        self.id = random.randint(1, 100000)

    def start(self):
        """Receives the trafic generated by _sendOutRandomTraffic().
        This should run on every Node, so we can choose targets at random."""
        recvprocess = subprocess.Popen(shlex.split("ITGRecv"))
        self.processes.append(recvprocess)
        recvprocess.wait()

    def stop(self, sender=None):
        """Shuts the bot down."""
        logging.info("Bot was stopped via signal from %s" % sender)
        super(RandomTrafficReceiver, self).stop()
        for proc in self.processes:
            proc.terminate()


class RandomTrafficSender(CommandExecutor):
    def __init__(self, probability=0, peerlist=["localhost"], **kwargs):
        super(RandomTrafficSender, self).__init__(**kwargs)

        self.probability = float(probability)
        assert 0 <= self.probability <= 1, "The probability has to be a float between 0 and 1"
        self.peerlist = peerlist

        self._simulated_apps = ["Telnet", "DNS", "Quake3", "CSa", "CSi", "VoIP -x G.723.1", "VoIP -h CRTP -VAD G.711.2"]

    def performDuty(self, *args, **kwargs):
        """Sends random traffic to a random host to generate noise in the network.
        ITGSend (belongs to D-ITG) is a traffic generator that sends out random traffic.
        It is able to simulate various application of which one is randomly chosen."""

        if random.uniform(0, 1) < self.probability:
            # We can ignore the log files, because we are just using the traffic as noise
            receiver = random.choice(self.peerlist)
            app = random.choice(self._simulated_apps)
            subprocess.call("ITGSend -a %s -l /dev/null -x /dev/null %s"
                            % (receiver, app), shell=True)
            writeLogentry(type(self).__name__, "Sent %s traffic to %s" % (app, receiver))