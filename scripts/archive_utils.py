"""ZIP output with fixed public metadata, never local timestamps or extended attributes."""
from pathlib import Path
import stat
import zipfile


class PublicZipFile(zipfile.ZipFile):
    def writestr(self, zinfo_or_arcname, data, compress_type=None, compresslevel=None):
        name = zinfo_or_arcname.filename if isinstance(zinfo_or_arcname, zipfile.ZipInfo) else str(zinfo_or_arcname)
        if name.startswith('/') or '..' in Path(name).parts:
            raise ValueError('Archive member must have a safe relative path')
        executable = isinstance(zinfo_or_arcname, zipfile.ZipInfo) and bool(zinfo_or_arcname.external_attr >> 16 & 0o111)
        info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
        info.create_system = 3
        mode = stat.S_IFDIR | 0o755 if name.endswith('/') else stat.S_IFREG | (0o755 if executable else 0o644)
        info.external_attr = mode << 16
        if name.endswith('/'):
            info.external_attr |= 0x10
        info.compress_type = self.compression if compress_type is None else compress_type
        return super().writestr(info, data, compress_type=info.compress_type, compresslevel=compresslevel)

    def write(self, filename, arcname=None, compress_type=None, compresslevel=None):
        path = Path(filename)
        if path.is_symlink() or any(parent.is_symlink() for parent in path.absolute().parents):
            raise ValueError('Symbolic links are not allowed in public archives')
        if not path.is_file():
            raise ValueError('Only regular files are allowed')
        info = zipfile.ZipInfo(str(arcname if arcname is not None else path.name))
        info.external_attr = (stat.S_IFREG | (0o755 if path.stat().st_mode & 0o111 else 0o644)) << 16
        self.writestr(info, path.read_bytes(), compress_type, compresslevel)
