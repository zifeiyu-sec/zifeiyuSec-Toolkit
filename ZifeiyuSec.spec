# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

project_root = Path(SPECPATH)
block_cipher = None


def tree_datas(relative_dir: str):
    root = project_root / relative_dir
    if not root.exists():
        return []
    return [(str(path), str(path.parent.relative_to(project_root))) for path in root.rglob('*') if path.is_file()]


datas = []
datas += tree_datas('data')
datas += tree_datas('docs')
datas += tree_datas('images')
datas += tree_datas('resources')
for extra_file in ('settings.example.ini', 'run_tool.vbs', 'README.md', 'LICENSE', 'image.ico', 'image.png', 'favicon.ico'):
    candidate = project_root / extra_file
    if candidate.exists():
        datas.append((str(candidate), '.'))

datas += collect_data_files('markdown')

hiddenimports = []
hiddenimports += collect_submodules('core')
hiddenimports += collect_submodules('ui')
hiddenimports += ['PyQt5.sip']

icon_path = project_root / 'image.ico'
if not icon_path.exists():
    fallback_icon = project_root / 'resources' / 'icons' / 'fox.ico'
    icon_path = fallback_icon if fallback_icon.exists() else None
exe_icon = str(icon_path) if icon_path else None


a = Analysis(
    ['main.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    name='ZifeiyuSec',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=exe_icon,
    exclude_binaries=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ZifeiyuSec',
)
