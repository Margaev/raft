import enum
import logging
import random
import json

from settings import settings
from service_discovery import ServiceDiscovery


class RaftState(enum.Enum):
    LEADER = 1
    FOLLOWER = 2
    CANDIDATE = 3


class Timeout:
    def __init__(self, timeout_min: int, timeout_max: int) -> None:
        self._timeout_min = timeout_min
        self._timeout_max = timeout_max
        self._timeout = None
        self.reset()

    def has_timed_out(self, clock) -> bool:
        if clock >= self._timeout:
            return True
        return False

    def reset(self) -> None:
        self._timeout = random.randint(self._timeout_min, self._timeout_max)


class RaftStateMachine:
    def __init__(self, address: str, port: int, sd: ServiceDiscovery) -> None:
        self.address = address
        self.port = port
        self.sd = sd
        self.term = 0
        self.voted_for = None
        self.votes_received = 0
        self.election_timeout = None
        self.clock = 0
        self._state = RaftState.FOLLOWER
        self.election_timeout = Timeout(
            timeout_min=settings.min_election_timeout,
            timeout_max=settings.max_election_timeout,
        )
        self.last_log_index = 0
        self.last_log_term = 0

    @property
    def state(self) -> RaftState:
        return self._state

    @state.setter
    def state(self, state: RaftState) -> None:
        self._state = state
        logging.info(f"Node is now in state {state}")

    def handle_clock(self) -> None:
        self.clock += 1
        op = data = None

        match self.state:
            case RaftState.FOLLOWER:
                if self.election_timeout.has_timed_out(clock=self.clock):
                    self.state = RaftState.CANDIDATE
            case RaftState.CANDIDATE:
                if self.election_timeout.has_timed_out(clock=self.clock):
                    self.election_timeout.reset()
                    self.clock = 0
                    self.votes_received = 0
                    op, data = self.start_election()
            case RaftState.LEADER:
                logging.info("Sending append_entries")
                op = "append_entries"
                # TODO implement append_entries
                data = {
                    "address": self.address,
                    "port": self.port,
                    "term": self.term,
                    "leader_id": (self.address, self.port),
                    "prev_log_index": self.last_log_index,
                    "prev_log_term": self.last_log_term,
                    "entries": [],
                    "leader_commit": 0,
                }
        return op, data

    def start_election(self) -> tuple[str, dict]:
        logging.info("Starting election")
        self.term += 1
        self.voted_for = (self.address, self.port)
        data = {
            "address": self.address,
            "port": self.port,
            "term": self.term,
            # "last_log_index": self.last_log_index,
            # "last_log_term": self.last_log_term,
        }
        return "request_vote", data
    
    def handle_response(self, op: str, data: dict) -> None:
        match op:
            case "response_vote":
                self.handle_response_vote(
                    vote_granted=data["vote_granted"],
                    term=data["term"],
                )
    
    def handle_request(self, op: str, data: dict) -> dict:
        response = None
        match op:
            case "request_vote":
                response = self.handle_request_vote(
                    address=data["address"],
                    port=data["port"],
                    term=data["term"],
                    # last_log_index=data["last_log_index"],
                    # last_log_term=data["last_log_term"],
                )
            case "append_entries":
                response = self.handle_append_entries(
                    term=data["term"],
                    leader_id=data["leader_id"],
                    prev_log_index=data["prev_log_index"],
                    prev_log_term=data["prev_log_term"],
                    entries=data["entries"],
                    leader_commit=data["leader_commit"],
                )
            
        logging.info(f"response: '{response}'")
        return response

    def handle_request_vote(
        self,
        address,
        port,
        term,
        # last_log_index,
        # last_log_term,
    ) -> dict:
        response = {"vote_granted": False, "term": self.term}
        # TODO last_log_index and last_log_term should be used to determine if the candidate is up to date
        if self.voted_for is None and term >= self.term:
            self.voted_for = (address, port)
            response["vote_granted"] = True
        return response
    
    # TODO Refactor copilot code
    def handle_append_entries(
        self,
        term,
        leader_id,
        prev_log_index,
        prev_log_term,
        entries,
        leader_commit,
    ) -> dict:
        response = {"term": self.term, "success": False}
        if term >= self.term:
            self.term = term
            self.state = RaftState.FOLLOWER
            self.voted_for = None
            self.votes_received = 0
            self.clock = 0
            response["success"] = True
            logging.info(f"Received append_entries from {leader_id}")
        return response

    def handle_response_vote(self, vote_granted, term):
        if vote_granted:
            self.votes_received += 1
            if self.votes_received >= len(self.sd.nodes) // 2 and self.votes_received >= 2:
            # if self.votes_received >= len(self.sd.nodes) // 2:
                self.state = RaftState.LEADER
                self.votes_received = 0
        else:
            if term > self.term:
                self.state = RaftState.FOLLOWER
                self.term = term
                self.voted_for = None
                self.votes_received = 0
