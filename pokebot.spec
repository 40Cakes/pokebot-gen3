# -*- mode: python ; coding: utf-8 -*-

app_name='pokebot'

a = Analysis(
    ['pokebot.py'],
    pathex=[],
    binaries=[],
    datas=[('sprites', 'sprites'), ('modules/data', 'modules/data')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=app_name,
)

import os
import pathlib
import shutil

current_dir = pathlib.Path(os.getcwd())
output_dir = pathlib.Path(DISTPATH) / app_name

shutil.copyfile(current_dir / 'LICENSE.txt', output_dir / 'LICENSE.txt')
shutil.copyfile(current_dir / 'Readme.md', output_dir / 'Readme.md')

os.mkdir(output_dir / 'profiles')
for file in (current_dir / 'profiles').glob('*.yml'):
    shutil.copyfile(file, output_dir / 'profiles' / file.name)
for file in (current_dir / 'profiles').glob('*.py'):
    shutil.copyfile(file, output_dir / 'profiles' / file.name)

os.mkdir(output_dir / 'roms')
shutil.copyfile(current_dir / 'roms' / '.gitkeep', output_dir / 'roms' / '.gitkeep')
