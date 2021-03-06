#!/usr/bin/env python2
# coding=UTF-8
"""This file implements a nameserver that can issue requests for an internal set of known domain names
 and register new domains via a web interface. The nameserver answers DNS queries on port 66/67."""
# !/usr/bin/env python2
# coding=UTF-8

import json, logging, random
from tornado.web import RequestHandler, Application
from twisted.internet import reactor, defer
from twisted.names import dns, error, server
from tornado.httpserver import HTTPServer

from resources import emu_config
from actors.AbstractBot import Runnable

known_hosts = {}
protocol = None
DNS_PORT = 53

class DynamicResolver(object):
    """
    A resolver which calculates the answers to certain queries based on an internal dictionary
    """

    def query(self, query, timeout=None):
        """Calculate the response to the given DNS query."""

        requested_hostname = query.name.name
        logging.debug("Received query for %s" % requested_hostname)

        if known_hosts.has_key(requested_hostname) and len(known_hosts[requested_hostname]) >= 1:
            resultingIP = random.sample(known_hosts[requested_hostname], 1)[0]
            answer = dns.RRHeader(name=requested_hostname,
                                  payload=dns.Record_A(address=resultingIP))
            answers = [answer]
            authority = []
            additional = []
            return defer.succeed((answers, authority, additional))
        else:
            return defer.fail(error.DomainError())


def rrUpdate(hostname="", address=""):
    """Updates the address of the given hostname"""

    if known_hosts.has_key(hostname):
        assert isinstance(known_hosts[hostname], list), "known_hosts[%s] is a %s"%(hostname, type(known_hosts[hostname]))
        known_hosts[hostname].append(address)
    else:
        known_hosts[hostname] = [address]
    logging.debug("Hostname %s is now known under address %s" % (hostname, address))


def runNameserver(dnsport):
    """Run the DNS server.
    :param dnsport: The port on which to listen for dns requests"""
    global protocol
    logging.debug("Nameserver starts on port %d"%dnsport)

    factory = server.DNSServerFactory(
        clients=[DynamicResolver()]
    )
    protocol = dns.DNSDatagramProtocol(controller=factory)
    reactor.listenUDP(dnsport, protocol)

def stopNameserver():
    global protocol
    assert protocol is not None
    protocol.stopProtocol()

class HostRegisterHandler(RequestHandler):
    """Allows the address of a given hostname to be set via HTTP POST and dumps all known domains on a HTTP GET"""

    registered_bots = dict()

    def get(self):
        self.set_header("Content-Type", "application/json")
        self.write(json.dumps(known_hosts))

    def post(self):
        self.set_header("Content-Type", "text/plain")
        hostname = self.get_body_argument("hostname")
        address = self.get_body_argument("address")

        rrUpdate(hostname, address)
        self.write("OK")


httpserver = None
def runWebserver():
    """Run a webserver that allows to register additonal domain names.
    Helper method so that the server can run in its own thread."""
    global httpserver
    logging.debug("Webserver starts on port %d"%emu_config.PORT)

    app = Application([("/register-host", HostRegisterHandler)], autoreload=False)
    httpserver = HTTPServer(app)
    server.listen(emu_config.PORT)


def stopWebserver():
    """Stops the webserver"""
    global httpserver
    assert httpserver is not None
    httpserver.stop()

class Nameserver(Runnable):
    """Runs a nameserver that answers dns queries on the given port and accepts new domains via a web interface."""

    def __init__(self, name="", peerlist=None):
        Runnable.__init__(self, name)

    def start(self, dnsport=DNS_PORT):
        reactor.callInThread(runWebserver)
        reactor.callInThread(runNameserver, dnsport)

    def stop(self):
        stopWebserver()
        stopNameserver()
