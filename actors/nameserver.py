#!/usr/bin/env python2.7
# coding=UTF-8
from twisted.internet import reactor, defer
from twisted.names import dns, error, server
from blinker import signal
import logging, json
from threading import Thread
from tornado.ioloop import IOLoop
from tornado.web import RequestHandler, Application

known_hosts = {"heise.de": b"11.22.33.44", "lokaler_horst": b"127.0.0.1"}
rr_update_signal = signal("rr-update")


class DynamicResolver(object):
    """
    A resolver which calculates the answers to certain queries based on an internal dictionary
    """

    def __init__(self):
        rr_update_signal.connect(rrUpdate)

    def query(self, query, timeout=None):
        """Calculate the response to a query."""
        requested_hostname = query.name.name
        logging.info("Received query for %s" % requested_hostname)

        if known_hosts.has_key(requested_hostname):
            answer = dns.RRHeader(name=requested_hostname,
                                  payload=dns.Record_A(address=known_hosts[requested_hostname]))
            answers = [answer]
            authority = []
            additional = []
            return defer.succeed((answers, authority, additional))
        else:
            return defer.fail(error.DomainError())


@rr_update_signal.connect
def rrUpdate(sender, hostname="", address=""):
    known_hosts[hostname] = address
    logging.info("Hostname %s is now known under address %s" % (hostname, address))


def runNameserver():
    """Run the DNS server."""
    logging.info("Nameserver starts")
    factory = server.DNSServerFactory(
        clients=[DynamicResolver()]
    )
    protocol = dns.DNSDatagramProtocol(controller=factory)
    reactor.listenUDP(10053, protocol)
    reactor.run()
    signal("stop").send()


class HostRegisterHandler(RequestHandler):
    registered_bots = dict()

    def get(self):
        self.set_header("Content-Type", "application/json")
        self.write(json.dumps(known_hosts))

    def post(self):
        self.set_header("Content-Type", "text/plain")
        hostname = self.get_body_argument("hostname")
        address = self.get_body_argument("address")

        rr_update_signal.send(self, hostname=hostname, address=address)
        self.write("OK")


def make_app():
    return Application([
        ("/register-host", HostRegisterHandler),
    ], autoreload=True)


def runWebserver():
    """Run a webserver that allows to register additonal domain names"""
    logging.info("Webserver starts")
    app = make_app()
    app.listen(8080)
    IOLoop.current().start()


def stopWebserver(sender):
    IOLoop.instance().stop()


if __name__ == '__main__':
    logging.basicConfig(format="%(threadName)s: %(message)s", level=logging.INFO)

    webthread = Thread(name="webserver_thread", target=runWebserver, args=())
    webthread.start()
    signal("stop").connect(stopWebserver)

    runNameserver()