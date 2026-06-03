# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['game_2d.py'],
    pathex=[],
    binaries=[],
    datas=[('assets\\audio_2d', 'assets\\audio_2d'), ('assets\\external_oga', 'assets\\external_oga'), ('assets\\kenney_particle_pack', 'assets\\kenney_particle_pack'), ('assets\\kenney_tiny_dungeon', 'assets\\kenney_tiny_dungeon'), ('assets\\ninja_adventure_pack', 'assets\\ninja_adventure_pack'), ('assets\\valley_maps', 'assets\\valley_maps'), ('assets\\valley_ruin_pack', 'assets\\valley_ruin_pack')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TienLoDoKiep2D',
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
    name='TienLoDoKiep2D',
)
