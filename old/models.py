import pydantic


class PersistentState(pydantic.BaseModel):
    current_term: int
    voted_for: int
    log: list


class VolatileState(pydantic.BaseModel):
    commit_index: int
    last_applied: int


class VolatileLeaderState(pydantic.BaseModel):
    next_index: dict
    match_index: dict


class AppendEntriesRequest(pydantic.BaseModel):
    term: int
    leader_id: int
    prev_log_index: int
    prev_log_term: int
    entries: list
    leader_commit: int


class AppendEntriesResponse(pydantic.BaseModel):
    term: int
    success: bool


class RequestVoteRequest(pydantic.BaseModel):
    term: int
    candidate_id: int
    last_log_index: int
    last_log_term: int


class RequestVoteResponse(pydantic.BaseModel):
    term: int
    vote_granted: bool
