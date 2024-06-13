import logging
import os

import message
from service_discovery import ServiceDiscovery
from raft_server import RaftServer
from raft_state_machine import RaftStateMachine
from settings import settings

logging.basicConfig(level=logging.DEBUG)

logging.info("Starting up")

# address = settings.task_name
# address = service_discovery.get_self_ip()
# port = settings.port
# nodes = service_discovery.get_nodes(service_name=settings.service_name, port=port)

logging.info(f"settings: {settings}")


def main():
    sd = ServiceDiscovery(
        service_name=settings.service_name,
        port=settings.port,
    )
    raft_state_machine = RaftStateMachine(
        address=sd.ip,
        port=sd.port,
        sd=sd,
    )
    s = RaftServer(
        raft_state_machine=raft_state_machine,
        protocol=message.FixedLengthHeaderProtocol(),
        hearbeat_interval=settings.heartbeat_interval,
        sd=sd,
    )
    logging.info(f"Starting up node at {sd.ip}:{sd.port}")
    s.run()


if __name__ == "__main__":
    main()
