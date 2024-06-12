from pydantic_settings import BaseSettings


class RaftSettings(BaseSettings):
    min_election_timeout: int = 5
    max_election_timeout: int = 25
    heartbeat_interval: int = 1
    port: int = 12121
    task_name: str
    service_name: str
    node_id: int


settings = RaftSettings()
