"""Exercise the real native binary against a stdlib-only local WebSocket test host.
By default no valid app keyDown is sent. --launch-finder explicitly tests activation.
"""
import base64
import hashlib
import json
from pathlib import Path
import socket
import struct
import subprocess
import sys
import time
import os

ROOT = Path(__file__).resolve().parent.parent
binary = Path(os.environ.get('DOCKDECK_TEST_BINARY', str(ROOT / 'dist/local.dockdeck.sdPlugin/bin/DockDeck.app/Contents/MacOS/DockDeck')))
if '--launch-finder' in sys.argv:
    checker = ROOT / '.build/frontmost'
    assert checker.is_file(), 'compile tests/frontmost.swift first'
    subprocess.run(['open', '-a', '/Applications/Elgato Stream Deck.app'], check=True)
    for _ in range(25):
        time.sleep(0.2)
        if subprocess.check_output([str(checker)], text=True).strip() == 'com.elgato.StreamDeck':
            break
    else:
        raise AssertionError('Cannot establish non-Finder foreground app before activation test')
server = socket.socket()
server.bind(('127.0.0.1', 0))
server.listen(1)
server.settimeout(15)
process = subprocess.Popen([str(binary), '-port', str(server.getsockname()[1]),
                            '-pluginUUID', 'test-registration', '-registerEvent', 'registerPlugin'])

try:
    connection, _ = server.accept()
    connection.settimeout(15)
    buffer = bytearray()
    while b'\r\n\r\n' not in buffer:
        buffer.extend(connection.recv(4096))
    headers, trailing = bytes(buffer).split(b'\r\n\r\n', 1)
    buffer = bytearray(trailing)
    key = next(line.split(b':', 1)[1].strip() for line in headers.split(b'\r\n') if line.lower().startswith(b'sec-websocket-key:'))
    accept = base64.b64encode(hashlib.sha1(key + b'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').digest())
    connection.sendall(b'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: ' + accept + b'\r\n\r\n')

    def read_bytes(count):
        while len(buffer) < count:
            received = connection.recv(max(4096, count - len(buffer)))
            if not received:
                raise EOFError('plugin disconnected')
            buffer.extend(received)
        result = bytes(buffer[:count]); del buffer[:count]
        return result

    def receive():
        head = read_bytes(2)
        assert head[0] & 0x0f == 1, 'expected text frame'
        length = head[1] & 0x7f
        if length == 126: length = struct.unpack('!H', read_bytes(2))[0]
        if length == 127: length = struct.unpack('!Q', read_bytes(8))[0]
        assert length < 1024 * 1024
        mask = read_bytes(4) if head[1] & 0x80 else None
        data = read_bytes(length)
        if mask: data = bytes(value ^ mask[i % 4] for i, value in enumerate(data))
        return json.loads(data)

    def send(value):
        data = json.dumps(value).encode()
        header = bytes([0x81, len(data)]) if len(data) < 126 else b'\x81\x7e' + struct.pack('!H', len(data))
        connection.sendall(header + data)

    def event(kind, suffix, context, column=0, row=0):
        return {'event': kind, 'action': 'local.dockdeck.' + suffix, 'context': context, 'device': 'test-device',
                'payload': {'controller': 'Keypad', 'coordinates': {'column': column, 'row': row}, 'settings': {}}}

    assert receive() == {'event': 'registerPlugin', 'uuid': 'test-registration'}
    send(event('willAppear', 'open', 'open-key'))
    assert receive()['event'] == 'setImage'
    assert receive()['event'] == 'setTitle'
    send(event('keyDown', 'open', 'open-key'))
    switch = receive()
    assert switch == {'event': 'switchToProfile', 'context': 'test-registration', 'device': 'test-device', 'payload': {'profile': 'Dock14', 'page': 0}}
    send({'event': 'deviceDidConnect', 'device': 'test-device', 'deviceInfo': {'type': 3}})
    send(event('keyDown', 'open', 'open-key'))
    assert receive()['payload']['profile'] == 'Dock14Mobile'
    send({'event': 'deviceDidConnect', 'device': 'test-device', 'deviceInfo': {'type': 0}})
    for slot in range(14):
        send(event('willAppear', 'slot', f'app-{slot}', slot % 5, slot // 5))
        image = receive()
        assert image['event'] == 'setImage' and image['context'] == f'app-{slot}'
        png = base64.b64decode(image['payload']['image'].split(',', 1)[1])
        assert png.startswith(b'\x89PNG\r\n\x1a\n')
        assert struct.unpack('!II', png[16:24]) == (144, 144)
        assert receive()['event'] == 'setTitle'
    send(event('willAppear', 'exit', 'exit-key', 4, 2))
    assert receive()['event'] == 'setImage'
    assert receive()['event'] == 'setTitle'
    send(event('keyDown', 'exit', 'exit-key', 4, 2))
    assert receive() == {'event': 'switchToProfile', 'context': 'test-registration', 'device': 'test-device', 'payload': {}}
    # Invalid slot and supplied path cannot become an app launch.
    invalid = event('willAppear', 'slot', 'invalid-key', -1, 0)
    invalid['payload']['settings'] = {'path': '/Applications/Calculator.app', 'command': 'touch /tmp/should-not-exist'}
    send(invalid)
    assert receive()['event'] == 'setImage'
    assert receive()['event'] == 'setTitle'
    send(event('keyDown', 'slot', 'invalid-key', -1, 0))
    assert receive() == {'event': 'showAlert', 'context': 'invalid-key'}
    send(event('willDisappear', 'open', 'open-key'))
    send(event('keyDown', 'open', 'open-key'))
    send(event('keyDown', 'exit', 'exit-key', 4, 2))
    assert receive()['payload'] == {}, 'disappeared contexts must not act'
    # A countdown starts only when the Dock exit key actually appears.
    import select
    send(event('willDisappear', 'exit', 'exit-key', 4, 2))
    opening = event('willAppear', 'open', 'timed-open')
    opening['payload']['settings'] = {'autoReturnSeconds': 0.2}
    send(opening)
    assert receive()['event'] == 'setImage'
    assert receive()['event'] == 'setTitle'
    pressed = event('keyDown', 'open', 'timed-open')
    pressed['payload'].pop('settings')
    send(pressed)
    assert receive()['payload']['profile'] == 'Dock14'
    time.sleep(0.3)
    assert not select.select([connection], [], [], 0)[0], 'must wait for visible Dock'
    send(event('willAppear', 'exit', 'timed-exit', 4, 2))
    assert receive()['event'] == 'setImage'
    assert receive()['event'] == 'setTitle'
    assert receive()['payload'] == {}, 'deadline must return'
    send(event('willDisappear', 'exit', 'timed-exit', 4, 2))
    send(pressed)
    assert receive()['payload']['profile'] == 'Dock14'
    send(event('willAppear', 'exit', 'cancel-exit', 4, 2))
    assert receive()['event'] == 'setImage'
    assert receive()['event'] == 'setTitle'
    send(event('willDisappear', 'exit', 'cancel-exit', 4, 2))
    time.sleep(0.3)
    assert not select.select([connection], [], [], 0)[0], 'leaving Dock cancels countdown'
    disabled = event('keyDown', 'open', 'timed-open')
    disabled['payload']['settings'] = {'autoReturnSeconds': 0}
    send(disabled)
    assert receive()['payload']['profile'] == 'Dock14'
    send(event('willAppear', 'exit', 'off-exit', 4, 2))
    assert receive()['event'] == 'setImage'
    assert receive()['event'] == 'setTitle'
    time.sleep(0.3)
    assert not select.select([connection], [], [], 0)[0], 'zero disables automatic return'
    # Countdown images change at second boundaries; the key still returns immediately.
    send(event('willDisappear', 'exit', 'off-exit', 4, 2))
    counting = event('keyDown', 'open', 'timed-open')
    counting['payload']['settings'] = {'autoReturnSeconds': 1.5}
    send(counting)
    assert receive()['payload']['profile'] == 'Dock14'
    send(event('willAppear', 'exit', 'count-exit', 4, 2))
    first = receive()
    assert first['event'] == 'setImage'
    assert receive()['event'] == 'setTitle'
    second = receive()
    assert second['event'] == 'setImage'
    assert first['payload']['image'] != second['payload']['image'], 'countdown image must change'
    assert receive()['event'] == 'setTitle'
    send(event('keyDown', 'exit', 'count-exit', 4, 2))
    assert receive()['payload'] == {}, 'manual press must return before countdown ends'
    send(event('willDisappear', 'exit', 'count-exit', 4, 2))
    time.sleep(1.1)
    assert not select.select([connection], [], [], 0)[0], 'manual return cancels automatic return'
    print('PASS: countdown, delayed visibility, cancellation and disabled setting')
    if '--launch-finder' in sys.argv:
        # Opt-in diagnostic: unlike the default suite, this brings Finder forward.
        checker = ROOT / '.build/frontmost'
        assert checker.is_file(), 'compile tests/frontmost.swift first'
        send(event('keyDown', 'slot', 'app-0', 0, 0))
        activated = False
        for _ in range(25):
            time.sleep(0.2)
            if subprocess.check_output([str(checker)], text=True).strip() == 'com.apple.finder':
                activated = True
                break
        assert activated, 'valid app key did not activate Finder'
        print('PASS: real plugin keyDown activated Finder through NSWorkspace')
    connection.close()
    assert process.wait(timeout=10) == 0
    print('PASS: native WebSocket registration, 14 PNG app keys, profile entry/return, invalid slot/settings, stale context, disconnect exit')
finally:
    if process.poll() is None:
        process.terminate(); process.wait(timeout=5)
    server.close()
