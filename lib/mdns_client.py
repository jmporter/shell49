from zeroconf import Zeroconf, ServiceBrowser
from collections import namedtuple
import time
import socket


class MdnsListener:

    def __init__(self):
        pass

    def listen(self, service="_repl._tcp.local.", seconds=5):
        """Listen for mDNS messages for specified time.

        Return list of responses.
        """
        self.devs = []
        try:
            zeroconf = Zeroconf()
            ServiceBrowser(zeroconf, "_repl._tcp.local.", self)
            time.sleep(seconds)
        finally:
            zeroconf.close()
        return self.devs

    def remove_service(self, zeroconf, type, name):
        pass

    def add_service(self, zeroconf, type, name):
        Service = namedtuple("Service", "hostname ip url port spec")
        info = zeroconf.get_service_info(type, name)
        ip = socket.inet_ntoa(info.address)
        url = info.server[:-1]
        port = info.port
        spec = info.name
        hostname = url[:url.find('.')]
        self.devs.append(Service(hostname=hostname, ip=ip,
                                 url=url, port=port, spec=spec))
