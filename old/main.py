import sys

from node import Node

from message import FixedLengthHeaderProtocol
from raft_server import RaftServer

NODES = [
    {"id": 1, "address": "raft_1"},
    {"id": 2, "address": "raft_2"},
    {"id": 3, "address": "raft_3"},
    {"id": 4, "address": "raft_4"},
    {"id": 5, "address": "raft_5"},
]


class NodeController:
    def __init__(self, node: Node, nodes: list):
        self.node = node
        self.nodes = nodes

    def run(self):
        self.node.server.run()


if __name__ == "__main__":
    node = Node(
        node_id=sys.arg[1],
        nodes=NODES,
        server=RaftServer(FixedLengthHeaderProtocol()),
    )

    nc = NodeController(
        node=node,
        nodes=NODES,
    )

    nc.run()
