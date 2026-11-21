#!/usr/bin/env python3
"""Managed, private Minecraft network bootstrap; no secrets are logged."""
import http.server
import json
import os
from pathlib import Path
import re
import secrets
import signal
import socket
import subprocess
import threading
import time


def warn(message):
    print(f'[network] {message}', flush=True)


def number(name, value, default, low, high):
    try:
        result = int(value)
        if low <= result <= high:
            return result
    except (ValueError, TypeError):
        pass
    warn(f'Invalid {name}; using {default}.')
    return default


def accepted(value):
    return value.strip().lower() == 'true'


def atomic(path, content, mode=0o600):
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(content)
    temporary.chmod(mode)
    temporary.replace(path)


def secret(path, supplied):
    valid = lambda s: bool(re.fullmatch(r'[A-Za-z0-9_-]{32,128}', s))
    stored = path.read_text().strip() if path.exists() else ''
    if valid(supplied):
        value = supplied
    elif valid(stored):
        warn('Invalid FORWARDING_SECRET; keeping the stored secret. Correct the shared variable on both services to rotate it.')
        value = stored
    else:
        warn('Invalid FORWARDING_SECRET; generated a private fail-closed secret. Set a matching valid secret on both services and redeploy to allow proxy connections.')
        value = secrets.token_hex(32)
    atomic(path, value)
    return value


def private_host(host):
    return bool(re.fullmatch(r'[a-zA-Z0-9](?:[a-zA-Z0-9.-]{0,230})\.railway\.internal', host))


def proxy_config(data, env):
    secret(data / 'forwarding.secret', env.get('FORWARDING_SECRET', ''))
    host = env.get('BACKEND_HOST', 'lobby.railway.internal')
    if not private_host(host):
        warn('Invalid BACKEND_HOST; using lobby.railway.internal. Keep all backends on the private network.')
        host = 'lobby.railway.internal'
    servers = {'lobby': f'{host}:25565'}
    extra = data / 'backends.json'
    if extra.exists():
        try:
            for name, host in json.loads(extra.read_text()).items():
                if re.fullmatch(r'[a-z][a-z0-9_-]{0,31}', name) and name != 'lobby' and private_host(host):
                    servers[name] = f'{host}:25565'
                else:
                    warn('Ignored an invalid extra backend entry in backends.json.')
        except (ValueError, AttributeError, TypeError):
            warn('Invalid backends.json; keeping only the lobby backend.')
    motd = env.get('MOTD', 'A Minecraft network on Railway')
    motd = ''.join(c for c in motd[:200] if ord(c) >= 32)
    maximum = number('MAX_PLAYERS', env.get('MAX_PLAYERS', '20'), 20, 1, 1000)
    rows = '\n'.join(f'{json.dumps(k)} = {json.dumps(v)}' for k, v in servers.items())
    atomic(data / 'velocity.toml', f'''config-version = "2.7"
bind = "[::]:25565"
motd = {json.dumps(motd, ensure_ascii=False)}
show-max-players = {maximum}
online-mode = true
force-key-authentication = true
prevent-client-proxy-connections = false
player-info-forwarding-mode = "modern"
forwarding-secret-file = "forwarding.secret"
announce-forge = false
kick-existing-players = false
ping-passthrough = "ALL"
sample-players-in-ping = false
enable-player-address-logging = false
[servers]
{rows}
try = ["lobby"]
[forced-hosts]
[advanced]
compression-threshold = 256
compression-level = -1
login-ratelimit = 3000
connection-timeout = 5000
read-timeout = 30000
haproxy-protocol = false
tcp-fast-open = false
bungee-plugin-message-channel = false
show-ping-requests = false
failover-on-unexpected-server-disconnect = true
announce-proxy-commands = false
log-command-executions = false
log-player-connections = false
[query]
enabled = false
''')


def yaml_patch(path, updates):
    import yaml
    try:
        config = yaml.safe_load(path.read_text()) if path.exists() else {}
        if not isinstance(config, dict):
            config = {}
    except yaml.YAMLError:
        warn(f'Invalid {path.name}; rebuilding managed settings. Original retained as .invalid.')
        path.rename(path.with_suffix(path.suffix + '.invalid'))
        config = {}
    def merge(current, changes):
        for key, value in changes.items():
            if isinstance(value, dict):
                if not isinstance(current.get(key), dict):
                    current[key] = {}
                merge(current[key], value)
            else:
                current[key] = value
    merge(config, updates)
    atomic(path, yaml.safe_dump(config, sort_keys=False))


def paper_config(data, env):
    value = secret(data / 'forwarding.secret', env.get('FORWARDING_SECRET', ''))
    (data / 'config').mkdir(exist_ok=True)
    yaml_patch(data / 'config/paper-global.yml', {'proxies': {'velocity': {'enabled': True, 'online-mode': True, 'secret': value}}})
    yaml_patch(data / 'spigot.yml', {'settings': {'bungeecord': False}})
    props = {}
    path = data / 'server.properties'
    if path.exists():
        for line in path.read_text().splitlines():
            if line and not line.lstrip().startswith(('#', '!')) and '=' in line:
                key, value = line.split('=', 1)
                props[key.strip()] = value
    whitelist = env.get('WHITELIST_ENABLED', 'false').strip().lower()
    if whitelist not in ('true', 'false'):
        warn('Invalid WHITELIST_ENABLED; enabling the whitelist to fail closed.')
        whitelist = 'true'
    props.update({'server-ip': '::', 'server-port': '25565', 'online-mode': 'false',
                  'enforce-secure-profile': 'false', 'enable-rcon': 'false', 'enable-query': 'false',
                  'white-list': whitelist, 'enforce-whitelist': whitelist,
                  'max-players': str(number('MAX_PLAYERS', env.get('MAX_PLAYERS', '20'), 20, 1, 1000)),
                  'view-distance': str(number('VIEW_DISTANCE', env.get('VIEW_DISTANCE', '6'), 6, 2, 16)),
                  'simulation-distance': str(number('SIMULATION_DISTANCE', env.get('SIMULATION_DISTANCE', '4'), 4, 2, 16))})
    props['motd'] = ''.join(c for c in env.get('MOTD', 'A Minecraft network on Railway')[:200] if ord(c) >= 32).replace('\\', '\\\\')
    props.setdefault('level-name', 'world')
    props.setdefault('gamemode', 'survival')
    props.setdefault('difficulty', 'normal')
    atomic(path, '\n'.join(f'{k}={v}' for k, v in sorted(props.items())) + '\n')
    atomic(data / 'eula.txt', 'eula=true\n')


def memory_limit_mb():
    for filename in ('/sys/fs/cgroup/memory.max', '/sys/fs/cgroup/memory/memory.limit_in_bytes'):
        try:
            value = int(Path(filename).read_text()) // 1048576
            if value < 1048576:
                return value
        except (OSError, ValueError):
            pass
    return None


def encode_varint(value):
    value &= 0xffffffff
    result = bytearray()
    while True:
        byte = value & 0x7f
        value >>= 7
        result.append(byte | (0x80 if value else 0))
        if not value:
            return bytes(result)


def read_varint(stream):
    value = 0
    for shift in range(0, 35, 7):
        byte = stream.read(1)
        if not byte:
            raise EOFError('Incomplete Minecraft VarInt')
        value |= (byte[0] & 0x7f) << shift
        if not byte[0] & 0x80:
            return value
    raise ValueError('Oversized Minecraft VarInt')


class DeadlineReader:
    def __init__(self, connection, deadline):
        self.connection = connection
        self.deadline = deadline

    def read(self, length):
        result = bytearray()
        while len(result) < length:
            remaining = self.deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('Minecraft status deadline exceeded')
            self.connection.settimeout(remaining)
            part = self.connection.recv(length - len(result))
            if not part:
                break
            result.extend(part)
        return bytes(result)


def minecraft_status(host, port=25565):
    """Require a bounded, valid Minecraft status response; an open port is insufficient."""
    import io
    import struct
    try:
        address = host.encode('utf-8')
        handshake = (b'\x00' + encode_varint(-1) + encode_varint(len(address))
                     + address + struct.pack('>H', port) + b'\x01')
        with socket.create_connection((host, port), timeout=2) as connection:
            connection.sendall(encode_varint(len(handshake)) + handshake + b'\x01\x00')
            stream = DeadlineReader(connection, time.monotonic() + 2)
            length = read_varint(stream)
            if not 1 <= length <= 32768:
                return None
            payload = stream.read(length)
            if len(payload) != length:
                return None
        packet = io.BytesIO(payload)
        if read_varint(packet) != 0:
            return None
        length = read_varint(packet)
        if not 1 <= length <= 32768:
            return None
        encoded = packet.read(length)
        if len(encoded) != length or packet.read(1):
            return None
        response = json.loads(encoded)
        if not isinstance(response, dict):
            return None
        version, players = response.get('version'), response.get('players')
        if not isinstance(version, dict) or not isinstance(players, dict):
            return None
        if not isinstance(version.get('name'), str) or not version['name']:
            return None
        if type(version.get('protocol')) is not int or version['protocol'] < 0:
            return None
        if type(players.get('online')) is not int or players['online'] < 0:
            return None
        if type(players.get('max')) is not int or players['max'] < 1:
            return None
        if not isinstance(response.get('description'), (str, dict)):
            return None
        return response
    except (OSError, ValueError, EOFError, UnicodeError, struct.error):
        return None


def network_ready(role, backend_host):
    local = minecraft_status('127.0.0.1')
    if local is None:
        return False
    if role == 'paper':
        return True
    backend = minecraft_status(backend_host)
    return (backend is not None and local['version'] == backend['version']
            and local['description'] == backend['description'])


def health_server(state, port, child_running=lambda: True):
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path not in ('/health', '/ready'):
                self.send_error(404)
                return
            snapshot = dict(state)
            if snapshot['state'] == 'ready' and not child_running():
                snapshot['state'] = 'failed'
            ready = snapshot['state'] == 'ready'
            intentionally_blocked = self.path == '/health' and snapshot['state'] == 'blocked'
            payload = json.dumps(snapshot).encode()
            self.send_response(200 if ready or intentionally_blocked else 503)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        def log_message(self, *args):
            pass
    return http.server.ThreadingHTTPServer(('0.0.0.0', port), Handler)


def main():
    role = os.environ.get('SERVER_ROLE', 'velocity')
    data = Path('/data')
    data.mkdir(exist_ok=True)
    os.chdir(data)
    state = {'state': 'starting', 'role': role}
    child = None
    stopping = threading.Event()
    def stop(signum, frame):
        state.update(state='stopping')
        stopping.set()
        if child is not None and child.poll() is None:
            child.terminate()
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    port = number('PORT', os.environ.get('PORT', '8080'), 8080, 1024, 65535)
    if port == 25565:
        warn('PORT conflicts with the game listener; using 8080 for health.')
        port = 8080
    server = health_server(state, port, lambda: child is not None and child.poll() is None and not stopping.is_set())
    threading.Thread(target=server.serve_forever, daemon=True).start()
    limit = memory_limit_mb()
    minimum = 1536 if role == 'paper' else 384
    if not accepted(os.environ.get('EULA', '')):
        state.update(state='blocked', reason='Set EULA=true only after accepting https://aka.ms/MinecraftEULA, then redeploy.')
    elif limit is not None and limit < minimum:
        state.update(state='blocked', reason=f'{role} needs at least {minimum} MiB container memory; use Hobby with 3-4 GB for Paper and 1 GB for Velocity.')
    else:
        if role == 'paper':
            paper_config(data, os.environ)
        else:
            proxy_config(data, os.environ)
        default_heap = 2048 if role == 'paper' else 384
        heap = number('HEAP_MB', os.environ.get('HEAP_MB', str(default_heap)), default_heap, 256, 32768)
        if limit is not None:
            heap = min(heap, max(256, limit - (768 if role == 'paper' else 192)))
        warn(f'Starting {role}: Java heap {heap} MiB; container cap {limit or "unlimited"} MiB. Paper recommends 3-4 GB total RAM; Trial/Free are unsuitable for this network.')
        command = ['java', f'-Xms{min(heap, 256)}M', f'-Xmx{heap}M', '-XX:ActiveProcessorCount=2', '-XX:+UseG1GC', '-jar', f'/opt/server/{role}.jar']
        if role == 'paper':
            command.append('--nogui')
        child = subprocess.Popen(command)
        backend_host = os.environ.get('BACKEND_HOST', 'lobby.railway.internal')
        if not private_host(backend_host):
            backend_host = 'lobby.railway.internal'
        while not stopping.is_set() and child.poll() is None:
            ready = network_ready(role, backend_host)
            if not stopping.is_set():
                state.update(state='ready' if ready else 'starting')
            stopping.wait(2)
        if stopping.is_set():
            try:
                child.wait(timeout=110)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
        else:
            state.update(state='failed', reason='Java exited; inspect logs and redeploy after correcting the problem.')
            server.shutdown()
            raise SystemExit(child.returncode or 1)
    if state['state'] == 'blocked':
        warn(state['reason'])
        while not stopping.wait(2):
            pass
    server.shutdown()


if __name__ == '__main__':
    main()
