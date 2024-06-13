import socket
import logging


class ServiceDiscovery:
    def __init__(self, service_name: str, port: int):
        self.service_name = service_name
        self.port = port
        self._nodes = []
        self._node_list_is_valid = False
        self._ip = None
    
    @property
    def ip(self):
        if not self._ip:
            self._ip = socket.gethostbyname(socket.gethostname())
        return self._ip

    @property
    def nodes(self):
        if not self._node_list_is_valid:
            logging.info(f"Nodes list is invalidated, fetching new nodes.")
            self._nodes = self._get_nodes()
            self._node_list_is_valid = True
        return self._nodes

    def _get_nodes(self):
        nodes = {
            (address_info[4][0], self.port)
            for address_info in socket.getaddrinfo(f"tasks.{self.service_name}", 0)
            if address_info[4][0] != self.ip
        }
        return list(nodes)
    
    def invalidate_nodes(self):
        self._node_list_is_valid = False
