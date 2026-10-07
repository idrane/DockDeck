"""Real OS deny tests against an app with exactly the production entitlements."""
import json
from pathlib import Path
import plistlib
import subprocess

root = Path(__file__).resolve().parent.parent
build = root / '.build'
production = root / 'dist/local.dockdeck.sdPlugin/bin/DockDeck.app'
expected = plistlib.loads((root / 'config/DockDeck.entitlements').read_bytes())
signed = subprocess.check_output(['codesign', '-d', '--entitlements', ':-', str(production)], stderr=subprocess.DEVNULL)
assert plistlib.loads(signed) == expected
assert expected == {
    'com.apple.security.app-sandbox': True,
    'com.apple.security.network.client': True,
    'com.apple.security.temporary-exception.shared-preference.read-only': ['com.apple.dock'],
    'com.apple.security.temporary-exception.files.home-relative-path.read-only': ['/Applications/'],
}
app = build / 'SandboxProbe.app'
(app / 'Contents/MacOS').mkdir(parents=True, exist_ok=True)
info = plistlib.loads((root / 'config/Info.plist').read_bytes())
info.update(CFBundleIdentifier='local.dockdeck.securityprobe', CFBundleExecutable='SandboxProbe')
(app / 'Contents/Info.plist').write_bytes(plistlib.dumps(info))
subprocess.run(['xcrun', 'swiftc', '-module-cache-path', str(build / 'ModuleCache'),
                str(root / 'tests/sandbox_probe.swift'), '-o', str(app / 'Contents/MacOS/SandboxProbe')], check=True)
for generated in [app, *app.rglob('*')]:
    for attribute in ['com.apple.FinderInfo', 'com.apple.ResourceFork']:
        if subprocess.run(['xattr', '-p', attribute, str(generated)], stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL).returncode == 0:
            subprocess.run(['xattr', '-d', attribute, str(generated)], check=True)
subprocess.run(['codesign', '--force', '--sign', '-', '--options', 'runtime',
                '--entitlements', str(root / 'config/DockDeck.entitlements'), str(app)], check=True)
sentinel = build / 'sandbox-sentinel.txt'
sentinel.write_text('synthetic test data; must remain unchanged')
try:
    result = subprocess.run([str(app / 'Contents/MacOS/SandboxProbe'), str(sentinel)],
                            capture_output=True, text=True, timeout=15)
    assert sentinel.read_text() == 'synthetic test data; must remain unchanged'
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)
    print(json.dumps(json.loads(result.stdout), indent=2))
finally:
    sentinel.unlink(missing_ok=True)
