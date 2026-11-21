import importlib.util
import io
import json
from pathlib import Path
import socket
import threading
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('launch', ROOT / 'services/velocity/launch.py')
launch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launch)


def varint(value):
    result = bytearray()
    while True:
        b = value & 0x7f
        value >>= 7
        result.append(b | (0x80 if value else 0))
        if not value:
            return bytes(result)


class ReadinessTests(unittest.TestCase):
    def serve_once(self, response):
        listener = socket.socket()
        listener.bind(('127.0.0.1', 0))
        listener.listen(1)
        port = listener.getsockname()[1]
        def serve():
            with listener:
                connection, _ = listener.accept()
                with connection:
                    connection.recv(4096)
                    connection.sendall(response)
        threading.Thread(target=serve, daemon=True).start()
        return port

    def test_closed_or_non_minecraft_listener_is_not_ready(self):
        self.assertTrue(hasattr(launch, 'minecraft_status'), 'Minecraft protocol probe is required')
        for response in (b'', b'HTTP/1.1 200 OK\r\n', b'\x80' * 6, b'\xff\xff\xff\x7f'):
            with self.subTest(response=response):
                port = self.serve_once(response)
                self.assertIsNone(launch.minecraft_status('127.0.0.1', port))

    def test_truncated_invalid_or_incomplete_status_is_not_ready(self):
        self.assertTrue(hasattr(launch, 'minecraft_status'), 'Minecraft protocol probe is required')
        for value in ('not json', '{}', '{"version": {"name": "Paper"}}'):
            encoded = value.encode()
            body = b'\x00' + varint(len(encoded)) + encoded
            port = self.serve_once(varint(len(body)) + body)
            self.assertIsNone(launch.minecraft_status('127.0.0.1', port))
        port = self.serve_once(b'\x20\x00\x10{}')
        self.assertIsNone(launch.minecraft_status('127.0.0.1', port))

    def test_real_status_packet_is_ready(self):
        self.assertTrue(hasattr(launch, 'minecraft_status'), 'Minecraft protocol probe is required')
        status = {'version': {'name': 'Paper 26.3', 'protocol': 777},
                  'players': {'max': 20, 'online': 0}, 'description': 'world'}
        encoded = json.dumps(status).encode()
        body = b'\x00' + varint(len(encoded)) + encoded
        port = self.serve_once(varint(len(body)) + body)
        self.assertEqual(launch.minecraft_status('127.0.0.1', port), status)

    def test_http_health_tracks_readiness_and_explicit_blocked_exceptions(self):
        self.assertTrue(hasattr(launch, 'health_server'), 'HTTP readiness server is required')
        state = {'state': 'starting', 'role': 'paper'}
        server = launch.health_server(state, 0)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        def code(path):
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}{path}', timeout=2) as response:
                    return response.status
            except urllib.error.HTTPError as error:
                return error.code
        try:
            for value, health, ready in [('starting', 503, 503), ('ready', 200, 200),
                                         ('starting', 503, 503), ('blocked', 200, 503),
                                         ('stopping', 503, 503), ('failed', 503, 503)]:
                state['state'] = value
                self.assertEqual(code('/health'), health, value)
                self.assertEqual(code('/ready'), ready, value)
        finally:
            server.shutdown()
            server.server_close()

    def test_proxy_needs_valid_matching_private_backend_status(self):
        local = {'version': {'name': 'Paper 26.3', 'protocol': 777}, 'players': {'online': 0, 'max': 20}, 'description': 'world'}
        original = launch.minecraft_status
        def response(value):
            if isinstance(value, bytes):
                return value
            encoded = json.dumps(value).encode()
            body = b'\x00' + varint(len(encoded)) + encoded
            return varint(len(body)) + body
        for backend, expected in ((local, True), (b'HTTP/1.1 200 OK\r\n', False), ({**local, 'description': 'different'}, False)):
            with self.subTest(backend=backend):
                local_port = self.serve_once(response(local))
                backend_port = self.serve_once(response(backend))
                with patch.object(launch, 'minecraft_status', side_effect=lambda host: original('127.0.0.1', local_port if host == '127.0.0.1' else backend_port)):
                    self.assertEqual(launch.network_ready('velocity', 'lobby.railway.internal'), expected)

    def test_dead_child_immediately_invalidates_cached_ready_health(self):
        state = {'state': 'ready', 'role': 'paper'}
        server = launch.health_server(state, 0, child_running=lambda: False)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            for path in ('/health', '/ready'):
                with self.assertRaises(urllib.error.HTTPError) as failed:
                    urllib.request.urlopen(f'http://127.0.0.1:{server.server_address[1]}{path}', timeout=2)
                self.assertEqual(failed.exception.code, 503)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

if __name__ == '__main__':
    unittest.main()
