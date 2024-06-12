import queue
import socket
import threading

from node import Node

import message


class Server:
    def __init__(self, protocol):
        self.protocol = protocol
        self.data = {}
        self.q = queue.Queue()

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", 12121))

        sock.listen()

        threading.Thread(target=self.handle_messages, daemon=True).start()
        threading.Thread(target=self.handle_messages, daemon=True).start()

        while True:
            client, address = sock.accept()
            print("received connection from", client, address)

            threading.Thread(target=self.handle_client, args=(client, address), daemon=True).start()

    def handle_client(self, client, address):
        print("received a connection")
        return_queue = queue.Queue()
        while True:
            msg = self.protocol.recv_message(client)

            self.q.put((return_queue, msg))

            # wait until i processed the message for the client here
            response = return_queue.get()
            self.protocol.send_message(client, response)

    def handle_messages(self):
        while True:
            (return_queue, msg) = self.q.get()
            op, rest = msg.split(" ", maxsplit=1)

            if op == "GET":
                return_queue.put(self.data.get(rest))

            elif op == "DEL":
                del self.data[rest]
                return_queue.put("ok")

            elif op == "SET":
                key, val = rest.split(" ", maxsplit=1)
                self.data[key] = val
                return_queue.put("ok")

            elif op == "INCR":
                key, val = rest.split(" ", maxsplit=1)
                self.data[key] += val
                return_queue.put("ok")

            else:
                print("unknown message")

    def send_messages(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(("localhost", 12121))

            while True:
                msg = input()

                self.protocol.send_message(sock, msg)
                print(self.protocol.recv_message(sock))
