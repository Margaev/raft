import json

class ClientDisconnected(Exception):
    pass


class FixedLengthHeaderProtocol:
    def __init__(self, header_length=64, header_byteorder="little"):
        self.header_length = header_length
        self.header_byteorder = header_byteorder

    def _receive_fixed(self, sock, length):
        data = b""

        while len(data) < length:
            msg_part = sock.recv(min(1024, length - len(data)))

            if not msg_part:
                raise ClientDisconnected()

            data += msg_part

        return data

    def recv_message(self, sock):
        header = self._receive_fixed(sock, self.header_length)
        msg_length = int.from_bytes(header, self.header_byteorder)
        message = self._receive_fixed(sock, msg_length)
        op, rest = message.decode("utf-8").split(" ", maxsplit=1)
        return op, json.loads(rest)

    def send_message(self, sock, op, data):
        msg = f"{op} {json.dumps(data)}"
        bytes_msg = msg.encode("utf-8")
        msg_length = len(bytes_msg)

        if msg_length >= 2**self.header_length:
            raise ValueError("msg is too long for header")

        header = msg_length.to_bytes(self.header_length, self.header_byteorder)

        sock.sendall(header)
        sock.sendall(bytes_msg)
