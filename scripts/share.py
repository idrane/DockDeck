#!/usr/bin/env python3
"""Package a clean entry profile and the locally built plugin; never read user profiles."""
import hashlib
import json
from pathlib import Path
import uuid
import zipfile
from archive_utils import PublicZipFile

root = Path(__file__).resolve().parent.parent
dist = root / 'dist'
plugin = dist / 'local.dockdeck.streamDeckPlugin'
assert plugin.is_file(), 'Run scripts/package.py first'
manifest = json.loads((dist / 'local.dockdeck.sdPlugin/manifest.json').read_text())
version = manifest['Version']

def identifier(label):
    return str(uuid.UUID(bytes=uuid.uuid5(uuid.NAMESPACE_DNS, 'local.dockdeck.share.' + label).bytes, version=4))

page_id, default_id = identifier('page'), identifier('default')
base = identifier('profile').upper() + '.sdProfile/'
profile = {'Device': {'Model': '20GAA9902', 'UUID': ''}, 'Name': 'DockDeck',
           'Pages': {'Current': page_id, 'Default': default_id, 'Pages': [page_id]}, 'Version': '3.0'}
action = {'ActionID': identifier('open'), 'Name': 'Open Dock',
          'UUID': 'local.dockdeck.open', 'LinkedTitle': True, 'Settings': {}, 'Resources': {},
          'State': 0, 'States': [{'ShowTitle': False, 'Title': ''}]}
page = {'Controllers': [{'Type': 'Keypad', 'Actions': {'0,0': action}}], 'Icon': '', 'Name': ''}
empty = {'Controllers': [{'Type': 'Keypad', 'Actions': {}}], 'Icon': '', 'Name': ''}
entry = dist / 'DockDeck.streamDeckProfile'
with PublicZipFile(entry, 'w', zipfile.ZIP_DEFLATED) as archive:
    for directory in [base, base+'Images/', base+'Profiles/'] + [
        base+'Profiles/'+p.upper()+s for p in [page_id, default_id] for s in ['/', '/Images/']]:
        archive.writestr(directory, '')
    for name, value in [('manifest.json', profile),
                        ('Profiles/'+page_id.upper()+'/manifest.json', page),
                        ('Profiles/'+default_id.upper()+'/manifest.json', empty)]:
        archive.writestr(base+name, json.dumps(value, ensure_ascii=False))

guide = "DockDeck App Sandbox beta\n\nRequires Apple Silicon, macOS 13+, Stream Deck 7.5+, and a 5-column, 3-row layout (hardware or Mobile). Other Macs and OS versions still require verification.\n\nInstall local.dockdeck.streamDeckPlugin. Select your device and usual profile, then drag DockDeck > Open Dock onto an empty key. Press the hardware key or tap it on Mobile; accept the bundled profile installation if prompted. Press an app to launch or focus it; press Return to go back.\n\nThe optional DockDeck.streamDeckProfile provides a separate entry screen. It is not required for existing profiles. The plugin is always required. Enter through Open Dock instead of selecting Mac Dock directly from the profile menu.\n\nSelect the Open Dock key to set Auto-return delay (seconds). Default: 0 (disabled). Enter a number up to 86400; 0, blank, or Disable turns it off. Countdown starts when Dock appears; app presses do not restart it. Leaving Dock cancels it.\n\nIf Return stops working after an update, fully quit and reopen Stream Deck, then enter through Open Dock again. This resolved a stale return target during testing.\n\nThe recipient's own Dock supplies up to 14 apps. No sender app list or device ID is bundled. Unpinned running apps use launch order, not exact manually rearranged Dock order.\n\nSecurity: App Sandbox; read-only Dock preferences and ~/Applications access; default system resources and private container access. No Accessibility, Screen Recording, Full Disk Access, administrator permission, shell/AppleScript, telemetry, or remote updater. Network client permission is enabled; code connects only to 127.0.0.1. The OS entitlement does not prohibit all external networking. No zero-risk guarantee.\n\nThis beta has not received Developer ID signing, notarization, Marketplace approval, or an independent security audit. Do not bypass security protections if blocked. SHA256SUMS.txt detects file changes; it does not authenticate the publisher.\n\nUninstall through Stream Deck's plugin manager, then remove unwanted DockDeck/Mac Dock profiles.\n"
hashes = ''.join(hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + p.name + '\n' for p in [plugin, entry])
share = dist / ('DockDeck-' + version + '-sandbox-beta.zip')
with PublicZipFile(share, 'w', zipfile.ZIP_DEFLATED) as archive:
    for path in [plugin, entry]:
        archive.write(path, path.name)
    archive.writestr('README.txt', guide)
    archive.write(root / 'LICENSE', 'LICENSE')
    archive.writestr('SHA256SUMS.txt', hashes)

# Validate both checksums and all entry actions; no local paths or personal settings.
with zipfile.ZipFile(share) as archive:
    for path in [plugin, entry]:
        assert archive.read(path.name) == path.read_bytes()
with zipfile.ZipFile(entry) as archive:
    loaded = json.loads(archive.read(base+'manifest.json'))
    assert loaded['Device']['UUID'] == ''
    loaded_page = json.loads(archive.read(base+'Profiles/'+page_id.upper()+'/manifest.json'))
    actions = loaded_page['Controllers'][0]['Actions']
    assert len(actions) == 1 and actions['0,0']['UUID'] == 'local.dockdeck.open'
    assert actions['0,0']['Settings'] == {}
print('PASS: share archive, checksums, clean entry profile, plugin dependency')
print(share)
