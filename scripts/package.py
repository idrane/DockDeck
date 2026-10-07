#!/usr/bin/env python3
"""Build a self-contained local plugin using Apple tools and Python's standard library."""
import hashlib
import json
from pathlib import Path
import subprocess
import uuid
import zipfile
from archive_utils import PublicZipFile
import argparse
import plistlib
import shutil
import os

parser = argparse.ArgumentParser()
parser.add_argument('--identity', help='Exact Developer ID Application signing identity; otherwise ad-hoc test build')
options = parser.parse_args()

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / '.build'
DIST = ROOT / 'dist'
PLUGIN_ID = 'local.dockdeck'
PLUGIN = DIST / (PLUGIN_ID + '.sdPlugin')
APP = BUILD / 'DockDeck.app'
VERSION = '0.3.1.0'
# Remove only this script's generated output, preventing legacy unsigned executables shipping.
if PLUGIN.exists():
    shutil.rmtree(PLUGIN)
for directory in [BUILD, DIST, PLUGIN / 'bin', PLUGIN / 'images']:
    directory.mkdir(parents=True, exist_ok=True)
if APP.exists():
    shutil.rmtree(APP)
(APP / 'Contents/MacOS').mkdir(parents=True)
shutil.copyfile(ROOT / 'config/Info.plist', APP / 'Contents/Info.plist')
architectures = []
for arch in ['arm64']:
    binary = BUILD / ('DockDeck-' + arch)
    subprocess.run(['xcrun', 'swiftc', '-swift-version', '5', '-O', '-warnings-as-errors',
                    '-target', arch + '-apple-macosx13.0', '-module-cache-path', str(BUILD / 'ModuleCache'),
                    *map(str, sorted((ROOT / 'Sources').glob('*.swift'))),
                    '-Xlinker', '-sectcreate', '-Xlinker', '__TEXT', '-Xlinker', '__info_plist',
                    '-Xlinker', str(ROOT / 'config/Info.plist'), '-o', str(binary)], check=True)
    architectures.append(str(binary))
subprocess.run(['lipo', '-create', *architectures, '-output', str(APP / 'Contents/MacOS/DockDeck')], check=True)
# Finder may attach presentation metadata to newly created .app folders.
# Strip only signing-incompatible metadata from our generated output, never quarantine.
for generated in [APP, *APP.rglob('*')]:
    for attribute in ['com.apple.FinderInfo', 'com.apple.ResourceFork']:
        present = subprocess.run(['xattr', '-p', attribute, str(generated)],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
        if present:
            subprocess.run(['xattr', '-d', attribute, str(generated)], check=True)
sign = ['codesign', '--force', '--sign', options.identity or '-', '--options', 'runtime',
        '--entitlements', str(ROOT / 'config/DockDeck.entitlements')]
if options.identity:
    if not options.identity.startswith('Developer ID Application:'):
        raise SystemExit('Use a Developer ID Application identity for distribution')
    sign.append('--timestamp')
subprocess.run([*sign, str(APP)], check=True)
subprocess.run(['codesign', '--verify', '--strict', str(APP)], check=True)
shutil.copytree(APP, PLUGIN / 'bin/DockDeck.app', copy_function=shutil.copyfile)
(PLUGIN / 'bin/DockDeck.app/Contents/MacOS/DockDeck').chmod(0o755)
# Asset writer is a build tool, never shipped in the sandboxed runtime.
asset_tool = BUILD / 'render-assets'
subprocess.run(['xcrun', 'swiftc', '-swift-version', '5', '-module-cache-path', str(BUILD / 'ModuleCache'),
                str(ROOT / 'Sources/DockModel.swift'), str(ROOT / 'Sources/IconRenderer.swift'),
                str(ROOT / 'tools/RenderAssets/main.swift'), '-o', str(asset_tool)], check=True)
subprocess.run([str(asset_tool), str(PLUGIN / 'images')], check=True)

def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')

def action(name, suffix, visible=True, image='key'):
    return {'Name': name, 'UUID': PLUGIN_ID + '.' + suffix, 'Icon': 'images/action',
            'Controllers': ['Keypad'], 'SupportedInMultiActions': False,
            'VisibleInActionsList': visible, 'UserTitleEnabled': False,
            'States': [{'Image': 'images/' + image, 'ShowTitle': False}],
            'Tooltip': name}

svg = '<svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 28 28">' + ''.join(
    f'<rect x="{x}" y="{y}" width="6" height="6" rx="1" fill="white"/>'
    for x in [3, 11, 19] for y in [3, 11, 19]) + '</svg>'
(PLUGIN / 'images/action.svg').write_text(svg)
manifest = {'UUID': PLUGIN_ID, 'Name': 'DockDeck', 'Author': 'Local Tools',
            'Description': 'Finder, pinned, running and recent Dock apps on 14 keys, plus return. Local only.',
            'Version': VERSION, 'SDKVersion': 2, 'CodePath': 'bin/DockDeck.app/Contents/MacOS/DockDeck',
            'Icon': 'images/plugin', 'Category': 'DockDeck', 'CategoryIcon': 'images/action',
            'OS': [{'Platform': 'mac', 'MinimumVersion': '13.0'}],
            'Software': {'MinimumVersion': '7.5'},
            'Actions': [action('Open Dock', 'open'),
                        action('Dock App', 'slot', False), action('Return', 'exit', False, 'exit')],
            'Profiles': [{'Name': 'Dock14', 'DeviceType': 0, 'Readonly': True,
                          'DontAutoSwitchWhenInstalled': True, 'AutoInstall': True},
                         {'Name': 'Dock14Mobile', 'DeviceType': 3, 'Readonly': True,
                          'DontAutoSwitchWhenInstalled': True, 'AutoInstall': True}]}
manifest['Actions'][0]['PropertyInspectorPath'] = 'ui/settings.html'
shutil.copytree(ROOT / 'ui', PLUGIN / 'ui')
shutil.copyfile(ROOT / 'LICENSE', PLUGIN / 'LICENSE')
write_json(PLUGIN / 'manifest.json', manifest)

# New profile IDs; no user profile, account data or device serial is copied.
def profile_uuid(name):
    return str(uuid.UUID(bytes=uuid.uuid5(uuid.NAMESPACE_DNS, PLUGIN_ID + name).bytes, version=4))
profile_id = profile_uuid('.profile').upper()
page_id = profile_uuid('.page')
default_id = profile_uuid('.default')
profile = {'Device': {'Model': '20GAA9902', 'UUID': ''}, 'Name': 'Dock14',
           'Pages': {'Current': page_id, 'Default': default_id, 'Pages': [page_id]}, 'Version': '3.0'}
actions = {}
for slot in range(15):
    suffix = 'slot' if slot < 14 else 'exit'
    actions[f'{slot % 5},{slot // 5}'] = {
        'ActionID': str(uuid.uuid5(uuid.NAMESPACE_DNS, PLUGIN_ID + f'.key{slot}')),
        'Name': 'Dock App' if slot < 14 else 'Return', 'UUID': PLUGIN_ID + '.' + suffix,
        'LinkedTitle': True, 'Settings': {}, 'Resources': {}, 'State': 0,
        'States': [{'ShowTitle': False, 'Title': ''}]}
page = {'Controllers': [{'Type': 'Keypad', 'Actions': actions}], 'Icon': '', 'Name': ''}
# Predefined archives must contain exactly one profile, unlike user import archives.
for profile_name, model in [('Dock14', '20GBL9901'), ('Dock14Mobile', 'VSD2/WiFi')]:
    with PublicZipFile(PLUGIN / (profile_name + '.streamDeckProfile'), 'w', zipfile.ZIP_DEFLATED) as archive:
        profile['Name'] = 'Mac Dock'
        profile['Device']['Model'] = model
        profile_id = profile_uuid('.profile.' + model).upper()
        base = profile_id + '.sdProfile/'
        for directory in [base, base + 'Images/', base + 'Profiles/',
                          base + 'Profiles/' + page_id.upper() + '/', base + 'Profiles/' + page_id.upper() + '/Images/',
                          base + 'Profiles/' + default_id.upper() + '/', base + 'Profiles/' + default_id.upper() + '/Images/']:
            archive.writestr(directory, '')
        archive.writestr(base + 'manifest.json', json.dumps(profile))
        archive.writestr(base + 'Profiles/' + page_id.upper() + '/manifest.json', json.dumps(page))
        archive.writestr(base + 'Profiles/' + default_id.upper() + '/manifest.json', json.dumps(
            {'Controllers': [{'Type': 'Keypad', 'Actions': {}}], 'Icon': '', 'Name': ''}))

installer = DIST / (PLUGIN_ID + '.streamDeckPlugin')
with PublicZipFile(installer, 'w', zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(PLUGIN.rglob('*')):
        if path.is_file():
            archive.write(path, path.relative_to(DIST))
(DIST / 'SHA256SUMS.txt').write_text(hashlib.sha256(installer.read_bytes()).hexdigest() + '  ' + installer.name + '\n')
print(installer)
