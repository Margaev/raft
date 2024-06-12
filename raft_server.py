import json
import logging
import queue
import socket
import threading
import time
from dataclasses import dataclass

import message
from raft_state_machine import RaftStateMachine


class RaftServer:
    def __init__(
        self,
        raft_state_machine: RaftStateMachine,
        protocol: message.FixedLengthHeaderProtocol,
        hearbeat_interval: int,
    ):
        self.raft_state_machine: RaftStateMachine = raft_state_machine
        self.protocol = protocol
        self.sockets = {}
        self.q = queue.Queue()
        self.server_socket = None
        self.heartbeat_interval = hearbeat_interval

    def init_server_socket(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.raft_state_machine.address, self.raft_state_machine.port))
        self.server_socket.listen()

    def handle_clients(self):
        while True:
            client, address = self.server_socket.accept()
            logging.info(f"received connection from {client}:{address}")
            threading.Thread(target=self.handle_client, args=(client, address), daemon=True).start()

    def handle_client(self, client: socket.socket, address: str):
        return_queue = queue.Queue()
        while True:
            op, data = self.protocol.recv_message(client)
            self.q.put((return_queue, op, data))
            # wait until the message is processed and a response is put into the return_queue
            response_op, response_data = return_queue.get()
            self.protocol.send_message(client, response_op, response_data)

    def run(self):
        self.init_server_socket()
        threading.Thread(target=self.handle_messages, daemon=True).start()
        threading.Thread(target=self.connect_to_nodes, daemon=True).start()
        threading.Thread(target=self.handle_clients, daemon=True).start()
        self.run_loop()

    def connect_to_nodes(self):
        for node_address, node_port in self.raft_state_machine.nodes:
            threading.Thread(
                target=self.connect_to_node,
                args=(node_address, node_port),
                daemon=True,
            ).start()

    def connect_to_node(self, address: str, port: int):
        while True:
            try:
                logging.info(f"Connecting to {address}:{port}...")
                # Create a new socket connection to the node and store it in self.sockets
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((address, port))
            except ConnectionRefusedError:
                logging.info(f"Connection to {address}:{port} refused, retrying in 1 second...")
                time.sleep(1)
            else:
                logging.info(f"Connected to {address}:{port}")
                self.sockets[(address, port)] = sock
                break

    def send_message_to_node(self, address: str, port: int, op: str, data: dict) -> tuple[str, dict]:
        response_op = response_data = None
        # Send a message to the node using the socket connection
        if (address, port) in self.sockets:
            sock = self.sockets[(address, port)]
            logging.info(f"Sending message to {address}:{port}")
            self.protocol.send_message(sock, op, data)
            response_op, response_data = self.protocol.recv_message(sock)
        else:
            logging.info(f"Connection to {address}:{port} not established")

        return response_op, response_data

    def run_loop(self):
        while True:
            time.sleep(self.heartbeat_interval)
            op, data = self.raft_state_machine.handle_clock()
            if op:
                for node_address, node_port in self.raft_state_machine.nodes:
                    response_op, response_data = self.send_message_to_node(node_address, node_port, op, data)
                    logging.info(f"received response from {node_address}:{node_port}: {response_op} {response_data}")
                    self.raft_state_machine.handle_response(response_op, response_data)

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
