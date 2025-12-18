# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['psce_main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('PoseScaleConfigEditor.ico', '.'),
        ('icons', 'icons')
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(
    a.pure,
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='PoseScaleConfigEditor',
    debug=False,
    strip=False,
    upx=True,
    icon='PoseScaleConfigEditor.ico',
    console=False,
)
