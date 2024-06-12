import models

from raft_server import RaftServer


class Node:
    def __init__(self, node_id, nodes, server: RaftServer):
        self.id = node_id
        self.nodes = nodes
        self.server = server
        self.persistent_state = models.PersistentState(current_term=0, voted_for=None, log=[])
        self.volatile_state = models.VolatileState(commit_index=0, last_applied=0)
        self.volatile_leader_state = models.VolatileLeaderState(next_index={}, match_index={})

    def request_vote(self, request: models.RequestVoteRequest): ...
