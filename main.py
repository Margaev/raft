import logging
import os

import message
import service_discovery
from raft_server import RaftServer
from raft_state_machine import RaftStateMachine
from settings import settings

logging.basicConfig(level=logging.DEBUG)

logging.info("Starting up")

# address = settings.task_name
address = service_discovery.get_self_ip()
port = settings.port
nodes = service_discovery.get_nodes(service_name=settings.service_name, port=port)

logging.info(f"settings: {settings}")


def main():
    raft_state_machine = RaftStateMachine(
        address=address,
        port=port,
        nodes=nodes,
    )
    s = RaftServer(
        raft_state_machine=raft_state_machine,
        protocol=message.FixedLengthHeaderProtocol(),
        hearbeat_interval=settings.heartbeat_interval,
    )
    logging.info(f"Starting up node at {address}:{port}")
    s.run()


if __name__ == "__main__":
    main()
