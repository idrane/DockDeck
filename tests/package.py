import json
from pathlib import Path
import zipfile
import uuid

root = Path(__file__).resolve().parent.parent
plugin = root / 'dist/local.dockdeck.sdPlugin'
manifest = json.loads((plugin / 'manifest.json').read_text())
assert (plugin / manifest['CodePath']).is_file()
assert {p['DeviceType'] for p in manifest['Profiles']} == {0, 3}
assert all(p['Readonly'] for p in manifest['Profiles'])
for profile_name, model in [('Dock14', '20GBL9901'), ('Dock14Mobile', 'VSD2/WiFi')]:
 with zipfile.ZipFile(plugin / (profile_name + '.streamDeckProfile')) as archive:
    umbrellas = [n for n in archive.namelist() if n.count('/') == 1 and n.endswith('manifest.json')]
    assert len(umbrellas) == 1, 'predefined archive must contain exactly one profile'
    assert json.loads(archive.read(umbrellas[0]))['Device']['Model'] == model
    for umbrella_name in umbrellas:
        umbrella = json.loads(archive.read(umbrella_name))
        base = umbrella_name.rsplit('/', 1)[0]
        pages = umbrella['Pages']
        assert pages['Pages'], 'Stream Deck requires a nonempty page list'
        assert pages['Current'] in pages['Pages']
        assert uuid.UUID(pages['Current']).version == 4
        assert f'{base}/Profiles/{pages["Current"].upper()}/' in archive.namelist()
        assert pages['Default'] not in pages['Pages'], 'pinned/default layer must be separate'
        default = json.loads(archive.read(f'{base}/Profiles/{pages["Default"].upper()}/manifest.json'))
        assert default['Controllers'][0]['Actions'] == {}
        page = json.loads(archive.read(f'{base}/Profiles/{pages["Current"].upper()}/manifest.json'))
        actions = page['Controllers'][0]['Actions']
        assert len(actions) == 15
        assert actions['4,2']['UUID'] == 'local.dockdeck.exit'
        assert sum(a['UUID'] == 'local.dockdeck.slot' for a in actions.values()) == 14
        assert set(actions) == {f'{c},{r}' for c in range(5) for r in range(3)}

with zipfile.ZipFile(root / 'dist/local.dockdeck.streamDeckPlugin') as archive:
    names = archive.namelist()
    assert all(n.startswith('local.dockdeck.sdPlugin/') and '..' not in n for n in names)
    assert not any('research/' in n for n in names)
    executable = archive.getinfo('local.dockdeck.sdPlugin/bin/DockDeck.app/Contents/MacOS/DockDeck')
    assert executable.external_attr >> 16 & 0o111
    assert 'local.dockdeck.sdPlugin/bin/DockDeck' not in names
print('PASS: native plugin archive, executable mode, nonempty profile page list, separate pinned layer, 14 app keys + exit')
