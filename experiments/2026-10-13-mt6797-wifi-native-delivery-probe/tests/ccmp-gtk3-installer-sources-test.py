#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise the actual GTK3 lookup with exact retained source bytes; no device."""
import importlib.util
import os
from pathlib import Path
import shutil
import sys
import tempfile

probe = Path(__file__).resolve().parents[1]
retained = Path(sys.argv[1]).resolve(strict=True)
with tempfile.TemporaryDirectory(prefix='ccmp-gtk3-sources-') as directory:
    root = Path(directory).resolve()
    credentials, sources = root / 'credentials', root / 'sources'
    credentials.mkdir()
    sources.mkdir()
    os.environ['GEMINI_PRIVATE_REPO'] = str(credentials)
    os.environ.pop('GEMINI_INSTALLER_SOURCE_ROOT', None)
    spec = importlib.util.spec_from_file_location('ccmp-gtk3_installer_sources', probe / 'install-ccmp-gtk3.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    default, _ = module.sources()
    assert default['pinned_sources'].__defaults__ == (credentials,)
    os.environ['GEMINI_INSTALLER_SOURCE_ROOT'] = str(sources)
    installer, _ = module.sources()
    assert installer['pinned_sources'].__defaults__ == (sources,)
    original, _ = module.ORIGINAL_SOURCES()
    assert installer['PINS'] == original['PINS']
    assert installer['derive'].__code__ == original['derive'].__code__
    assert installer['digest'].__code__ == original['digest'].__code__
    for name, digest in installer['PINS'].items():
        data = (retained / name).read_bytes()
        assert installer['digest'](data) == digest
        path = sources / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    accepted = installer['pinned_sources']()
    assert set(accepted) == set(installer['PINS'])
    assert not list(credentials.iterdir())  # source lookup copied no credentials
    name = next(iter(installer['PINS']))
    path = sources / name
    path.write_bytes(path.read_bytes() + b'\n')
    try:
        installer['pinned_sources']()
    except ValueError as error:
        assert 'reviewed installer input changed' in str(error)
    else:
        raise AssertionError('changed historical source accepted')
    path.unlink()
    path.symlink_to(retained / name)
    try:
        installer['pinned_sources']()
    except ValueError:
        pass
    else:
        raise AssertionError('symlinked historical source accepted')
    assert os.environ['GEMINI_PRIVATE_REPO'] == str(credentials)
print('GTK3 installer sources: PASS default/separate roots, unchanged pins/derive, mutation/symlink refusal')
