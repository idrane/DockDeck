#!/usr/bin/env python3
"""Read-only release checks on the actual installer, extracted into temporary storage.
Does not submit to Apple, alter security settings, or treat passing as QA approval.
"""
import argparse
import json
from pathlib import Path
import plistlib
import subprocess
import tempfile
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument('installer', type=Path)
args = parser.parse_args()
failures = []

def check(condition, label):
    print(('PASS: ' if condition else 'BLOCKED: ') + label)
    if not condition:
        failures.append(label)

def run(*cmd):
    return subprocess.run(cmd, capture_output=True)

with tempfile.TemporaryDirectory(prefix='dockdeck-release-') as directory:
    destination = Path(directory)
    with zipfile.ZipFile(args.installer) as archive:
        for entry in archive.infolist():
            path = Path(entry.filename)
            if path.is_absolute() or '..' in path.parts or (entry.external_attr >> 16 & 0o170000) == 0o120000:
                raise SystemExit('Unsafe archive path or symlink')
        archive.extractall(destination)
        for entry in archive.infolist():
            path = destination / entry.filename
            if path.is_file():
                path.chmod((entry.external_attr >> 16 & 0o777) or 0o644)
    manifests = list(destination.glob('*.sdPlugin/manifest.json'))
    if len(manifests) != 1:
        raise SystemExit('Expected exactly one plugin manifest')
    plugin = manifests[0].parent
    manifest = json.loads(manifests[0].read_text())
    check(manifest.get('Author') not in (None, '', 'Local Tools'), 'publisher metadata finalized')
    app = plugin / 'bin/DockDeck.app'
    check(run('codesign', '--verify', '--strict', str(app)).returncode == 0, 'packaged signature intact')
    details = run('codesign', '-dv', '--verbose=4', str(app)).stderr.decode(errors='replace')
    signed = 'Authority=Developer ID Application:' in details and 'TeamIdentifier=not set' not in details
    check(signed, 'Developer ID Application signature')
    check('runtime' in details, 'hardened runtime enabled')
    check('Timestamp=' in details, 'secure signing timestamp')
    result = run('codesign', '-d', '--entitlements', ':-', str(app))
    expected = plistlib.loads((Path(__file__).resolve().parent.parent / 'config/DockDeck.entitlements').read_bytes())
    try:
        actual = plistlib.loads(result.stdout)
    except (ValueError, plistlib.InvalidFileException):
        actual = {}
    check(actual == expected, 'signed sandbox permissions match reviewed policy')
    if signed:
        check(run('xcrun', 'stapler', 'validate', str(app)).returncode == 0, 'stapled notarization ticket valid')
        check(run('spctl', '--assess', '--type', 'execute', str(app)).returncode == 0, 'Gatekeeper assessment accepted')
    else:
        check(False, 'notarization / Gatekeeper checks require distribution signature')

print('Separate downloaded-Mac installation and hardware QA are still required.')
raise SystemExit(1 if failures else 0)
