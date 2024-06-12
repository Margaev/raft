import socket
import logging


def get_self_ip():
    return socket.gethostbyname(socket.gethostname())


def get_nodes(service_name: str, port: int):
    self_ip = get_self_ip()
    nodes = {
        (address_info[4][0], port)
        for address_info in socket.getaddrinfo(f"tasks.{service_name}", 0)
        if address_info[4][0] != self_ip
    }
    return list(nodes)
