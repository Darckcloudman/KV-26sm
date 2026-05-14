# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['smp12c_vibrodiag/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('test_data', 'test_data'),
    ],
    hiddenimports=[
        'numpy',
        'scipy',
        'matplotlib',
        'PyQt5',
        'matplotlib.backends.backend_qt5agg',
        'matplotlib.backends.backend_qt5',
    ],
    excludes=['PIL._avif'],
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

# Для сборки в ОДИН EXE файл используйте этот блок:
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SMP12C_VibroDiag',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    temp_dir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

# Если нужна не один файл, а папка с зависимостями, раскомментируйте:
# coll = COLLECT(
#     exe,
#     a.binaries,
#     a.zipfiles,
#     a.datas,
#     strip=False,
#     upx=True,
#     upx_exclude=[],
#     name='SMP12C_VibroDiag',
# )
