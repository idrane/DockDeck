#!/usr/bin/env python3
"""Explicit release operation: submit the signed app to Apple using an existing Keychain profile.
Never accepts passwords/API keys or modifies system security policy.
"""
import argparse
import json
from pathlib import Path
import subprocess
import zipfile
from archive_utils import PublicZipFile
import hashlib

parser = argparse.ArgumentParser()
parser.add_argument('--keychain-profile', required=True)
options = parser.parse_args()
root = Path(__file__).resolve().parent.parent
plugin = root / 'dist/local.dockdeck.sdPlugin'
app = plugin / 'bin/DockDeck.app'
details = subprocess.run(['codesign', '-dv', '--verbose=4', str(app)], capture_output=True, text=True, check=True).stderr
if 'Authority=Developer ID Application:' not in details or 'TeamIdentifier=not set' in details:
    raise SystemExit('Blocked: first build with a valid Developer ID Application identity. Ad-hoc builds cannot be released.')
subprocess.run(['codesign', '--verify', '--strict', str(app)], check=True)
upload = root / '.build/DockDeck-notarization.zip'
subprocess.run(['ditto', '-c', '-k', '--keepParent', str(app), str(upload)], check=True)
result = subprocess.run(['xcrun', 'notarytool', 'submit', str(upload), '--keychain-profile',
                         options.keychain_profile, '--wait', '--output-format', 'json'],
                        capture_output=True, text=True, check=True)
report = json.loads(result.stdout)
(root / 'dist/notarization-result.json').write_text(json.dumps(report, indent=2) + '\n')
if report.get('status') != 'Accepted':
    raise SystemExit('Blocked: Apple notarization was not accepted. See notarization-result.json.')
subprocess.run(['xcrun', 'stapler', 'staple', str(app)], check=True)
subprocess.run(['xcrun', 'stapler', 'validate', str(app)], check=True)
subprocess.run(['spctl', '--assess', '--type', 'execute', '--verbose=2', str(app)], check=True)
installer = root / 'dist/local.dockdeck.streamDeckPlugin'
with PublicZipFile(installer, 'w', zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(plugin.rglob('*')):
        if path.is_file(): archive.write(path, path.relative_to(plugin.parent))
(root / 'dist/SHA256SUMS.txt').write_text(hashlib.sha256(installer.read_bytes()).hexdigest() + '  ' + installer.name + '\n')
print('Accepted, stapled, assessed and repackaged. Run share.py again; do not rebuild after stapling.')
