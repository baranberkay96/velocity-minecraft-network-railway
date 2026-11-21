#!/usr/bin/env python3
"""Minecraft status and unauthenticated direct-backend rejection probes."""
import json
import socket
import struct
import sys
import uuid


def varint(value):
    value &= 0xffffffff
    result = bytearray()
    while True:
        b = value & 0x7f
        value >>= 7
        result.append(b | (0x80 if value else 0))
        if not value:
            return bytes(result)


def read_varint(stream):
    value = 0
    for shift in range(0, 35, 7):
        b = stream.read(1)
        if not b:
            raise EOFError('connection closed')
        value |= (b[0] & 0x7f) << shift
        if not b[0] & 0x80:
            return value
    raise ValueError('invalid VarInt')


def string(value):
    b = value.encode()
    return varint(len(b)) + b


def send(sock, body):
    sock.sendall(varint(len(body)) + body)


def packet(stream):
    size = read_varint(stream)
    body = stream.read(size)
    if len(body) != size:
        raise EOFError('incomplete packet')
    import io
    body = io.BytesIO(body)
    return read_varint(body), body


def connect(host, port, protocol, intention):
    sock = socket.create_connection((host, port), timeout=15)
    send(sock, varint(0) + varint(protocol) + string(host) + struct.pack('>H', port) + varint(intention))
    return sock


def status(host, port):
    with connect(host, port, -1, 1) as sock:
        send(sock, b'\x00')
        kind, body = packet(sock.makefile('rb'))
        assert kind == 0, kind
        return json.loads(body.read(read_varint(body)))


def reject_direct(host, port, protocol, tampered=False):
    with connect(host, port, protocol, 2) as sock:
        stream = sock.makefile('rb')
        send(sock, b'\x00' + string('ForwardProbe') + uuid.uuid4().bytes)
        kind, body = packet(stream)
        assert kind == 4, f'expected modern forwarding request, received packet {kind}'
        transaction = read_varint(body)
        channel = body.read(read_varint(body)).decode()
        assert channel == 'velocity:player_info', channel
        # Vanilla clients cannot answer the authenticated Velocity forwarding query.
        if tampered:
            forged = b'\x00' * 32 + varint(1) + string('127.0.0.1') + uuid.uuid4().bytes + string('ForwardProbe') + varint(0)
            send(sock, b'\x02' + varint(transaction) + b'\x01' + forged)
        else:
            send(sock, b'\x02' + varint(transaction) + b'\x00')
        kind, body = packet(stream)
        assert kind == 0, f'expected disconnect, received packet {kind}'
        reason = body.read()
        assert any(word in reason.lower() for word in (b'velocity', b'proxy', b'verify')), reason
        return {'query': channel, 'disconnect_hex': reason.hex()}


if __name__ == '__main__':
    proxy, backend = sys.argv[1:3]
    proxied = status(proxy, 25565)
    direct = status(backend, 25565)
    assert '26.3' in direct['version']['name'], direct
    assert proxied['version']['protocol'] == direct['version']['protocol'], (proxied, direct)
    assert proxied['description'] == direct['description'], (proxied, direct)
    result = {'proxy_status': proxied, 'backend_status': direct,
              'direct_backend_rejection': reject_direct(backend, 25565, direct['version']['protocol']),
              'tampered_mac_rejection': reject_direct(backend, 25565, direct['version']['protocol'], tampered=True)}
    print(json.dumps(result, indent=2))
