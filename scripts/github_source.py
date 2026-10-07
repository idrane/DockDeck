#!/usr/bin/env python3
"""Export only DockDeck source files, excluding unrelated work and private artifacts."""
from pathlib import Path
import zipfile
from archive_utils import PublicZipFile

root = Path(__file__).resolve().parent.parent
names = ['README.md', 'SECURITY.md', 'RESEARCH.md', 'RELEASE.md', 'CHANGELOG.md', '.gitignore', 'LICENSE']
files = [root / name for name in names if (root / name).is_file()]
for directory, suffixes in {
    'Sources': {'.swift'}, 'config': {'.plist', '.entitlements'},
    'scripts': {'.py', '.sh'}, 'tests': {'.py', '.sh', '.swift'},
    'tools': {'.swift'}, 'ui': {'.html', '.js', '.css'},
}.items():
    files.extend(p for p in (root / directory).rglob('*') if p.is_file() and p.suffix in suffixes and '__pycache__' not in p.parts)
output = root / 'dist/DockDeck-source.zip'
output.parent.mkdir(exist_ok=True)
with PublicZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(files):
        archive.write(path, Path('DockDeck') / path.relative_to(root))
print(f'{output} ({len(files)} source files; no binaries, user profiles or unrelated projects)')
