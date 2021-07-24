# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(
    ['src/pygsaw.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('./resources/images/apartments.jpg', 'resources/images'),
        ('./resources/images/kitten.png', 'resources/images'),
        ('./resources/icon/pygsaw_icon.ico', 'resources/icon'),
        ('./saves', 'saves'),
        ('./resources/background_images/TexturesCom_ConcreteBare0115_1_seamless_S.jpg', 'resources/background_images'),
        ('./sql/*.sql', 'sql')
    ],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)
pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='pygsaw',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    icon='resources/icon/pygsaw_icon.ico'
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='pygsaw'
)
