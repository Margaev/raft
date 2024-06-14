import json
import logging
import queue
import socket
import threading
import time
from dataclasses import dataclass

import message
from raft_state_machine import RaftStateMachine
from service_discovery import ServiceDiscovery


class RaftServer:
    def __init__(
        self,
        raft_state_machine: RaftStateMachine,
        protocol: message.FixedLengthHeaderProtocol,
        hearbeat_interval: int,
        sd: ServiceDiscovery,
    ):
        self.raft_state_machine: RaftStateMachine = raft_state_machine
        self.protocol = protocol
        self.q = queue.Queue()
        self.server_socket = None
        self.heartbeat_interval = hearbeat_interval
        self.sd = sd

    def init_server_socket(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.raft_state_machine.address, self.raft_state_machine.port))
        self.server_socket.listen()

    def handle_clients(self):
        while True:
            client, address = self.server_socket.accept()
            address = address[0]
            logging.info(f"received connection from {client}:{address}")
            if (address, self.sd.port) not in self.sd.nodes:
                self.sd.invalidate_nodes()
            threading.Thread(target=self.handle_client, args=(client, address), daemon=True).start()

    def handle_client(self, client: socket.socket, address: str):
        return_queue = queue.Queue()
        while True:
            try:
                op, data = self.protocol.recv_message(client)
                self.q.put((return_queue, op, data))
                # wait until the message is processed and a response is put into the return_queue
                response_op, response_data = return_queue.get()
                self.protocol.send_message(client, response_op, response_data)
            except message.ClientDisconnected:
                break

    def run(self):
        self.init_server_socket()
        threading.Thread(target=self.handle_messages, daemon=True).start()
        threading.Thread(target=self.handle_clients, daemon=True).start()
        self.run_loop()

    def send_message_to_node(self, address: str, port: int, op: str, data: dict) -> tuple[str, dict]:
        response_op = response_data = None
        # Send a message to the node using the socket connection
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((address, port))
            logging.info(f"Sending message to {address}:{port}")
            self.protocol.send_message(sock, op, data)
            response_op, response_data = self.protocol.recv_message(sock)

        return response_op, response_data

    def send_message_and_handle_response(self, address: str, port: int, op: str, data: dict) -> None:
        try:
            response_op, response_data = self.send_message_to_node(address, port, op, data)
        except message.ClientDisconnected:
            logging.info(f"client {address}:{port} disconnected")
            self.sd.invalidate_nodes()
        except OSError:
            logging.error(f"error sending message to {address}:{port}")
            self.sd.invalidate_nodes()
        else:
            logging.info(f"received response from {address}:{port}: {response_op} {response_data}")
            self.raft_state_machine.handle_response(response_op, response_data)

    def broadcast_message(self, op: str, data: dict):
        """
        Threaded function to broadcast a message to all nodes in the cluster
        """
        for node_address, node_port in self.sd.nodes:
            threading.Thread(target=self.send_message_and_handle_response, args=(node_address, node_port, op, data), daemon=True).start()

    def run_loop(self):
        while True:
            time.sleep(self.heartbeat_interval)
            op, data = self.raft_state_machine.handle_clock()
            if op:
                self.broadcast_message(op, data)

    def handle_messages(self):
        while True:
            (return_queue, op, data) = self.q.get()
            logging.info(f"received message: op = {op}, data = {data}")
            match op:
                case "tick":
                    logging.info(f"received tick with data {data}")
                    return_queue.put("ok", {})
                case "request_vote":
                    response_data = self.raft_state_machine.handle_request(op, data)
                    return_queue.put(("response_vote", response_data))
                case "append_entries":
                    response_data = self.raft_state_machine.handle_request(op, data)
                    return_queue.put(("response_append_entries", response_data))
