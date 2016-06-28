#!/usr/bin/env python2.7
# coding=UTF-8
import logging, random, time, os
from abc import ABCMeta, abstractmethod
from blinker import signal
from threading import Timer, Thread, current_thread

import emu_config

class Runnable(object):
    """A class that executes code, similar to the Java class of the same name"""
    __metaclass__ = ABCMeta

    def __init__(self, name=""):
        self.stopthread = False
        self.name = name
        signal('start').connect(self.start)
        signal('start ' + name).connect(self.start)
        signal('stop').connect(self.stop)
        signal('stop ' + name).connect(self.stop)

    @abstractmethod
    def start(self):
        """Starts the runnable so that it will perform its work. This may also be invoked by sending a start signal."""

    @abstractmethod
    def stop(self):
        """Stops the runnable so that it will not perform any further work until restartet.
        Its Thread may now safely be joined without the joining thread being blocked.
        This can alternatively be invoked by sending a stop signal."""


class AbstractBot(Runnable):
    """The abstract base class for all bots in the simulated botnets"""
    __metaclass__ = ABCMeta

    def __init__(self, peerlist=[], desinfect_timeout=10, probability_of_disinfection=0, name=""):
        Runnable.__init__(self, name=name)
        assert isinstance(peerlist, list), "type(peerlist): %s" % type(peerlist)

        self.peerlist = peerlist
        self.id = random.randint(1, 100000)
        self.disinfect_timeout = desinfect_timeout
        self.probability_of_disinfection = probability_of_disinfection

    def start(self, pauseBetweenDuties=15, args=()):
        """Starts the runnable, so that it performs its duties"""
        thread = Thread(name="Runnable %s" % self.name, target=self.doWork, args=(pauseBetweenDuties, args))
        thread.start()
        logging.debug("Started performing duties every %d seconds" % pauseBetweenDuties)

    def doWork(self, pauseBetweenDuties, args):
        """Does the actual work of this Runnable instance. Meant to be executed in a separate thread"""
        assert "Runnable" in current_thread().name
        while not self.stopthread:
            self.performDuty(args)
            self.desinfect_thread()
            time.sleep(pauseBetweenDuties)

    def desinfect_thread(self):
        """Simulates a desinfection of this Bot. Will only be executed with the given probability."""

        assert 0 <= self.probability_of_disinfection <= 1, \
            "The probability that a Bot gets disinfected has to be a number between 0 and 1. " \
            "Please check the Arguments to the AbstractBot constructor (or a class derived from it)."

        if random.uniform(0, 1) < self.probability_of_disinfection:
            # The second parameter is mandated by the API but has no actual use
            os.execv(emu_config.basedir + "/actors/Bot.py", ["useless"])
        else:
            Timer(self.disinfect_timeout, self.desinfect_thread, args=[]).start()

    @abstractmethod
    def performDuty(self, args):
        """Does the actual work"""

    def stop(self, sender=None):
        logging.info("Catched stop signal from %s" % sender)
        self.stopthread = True

def executeBot(bot, pauseBetweenDuties):
    assert isinstance(bot, Runnable)
    bot.start(pauseBetweenDuties=pauseBetweenDuties)