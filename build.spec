# -*- mode: python ; coding: utf-8 -*-
# Generar el .exe portable corriendo (en Windows, con el venv activado):
#     pyinstaller build.spec
#
# El resultado queda en dist/KlipperSync.exe — un solo archivo, no
# necesita instalación. Copialo junto a printers.json (se crea solo la
# primera vez, al lado del .exe) a donde quieras, incluso un pendrive.

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets/icon.ico', 'assets'), ('assets/fixer.png', 'assets')],
    hiddenimports=['paramiko', 'requests'],
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
    a.binaries,
    a.datas,
    [],
    name='KlipperSync',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # sin consola detras (app grafica)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico',  # opcional: descomentá y poné tu propio .ico en assets/
)
# Nota: al pasar a.binaries y a.datas directo al EXE (sin usar COLLECT
# despues), PyInstaller genera un unico archivo ejecutable (--onefile).
