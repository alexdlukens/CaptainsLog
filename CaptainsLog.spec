# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(
    ['main_script.py'],
    pathex=['./src/'],
    binaries=[],
    datas=[('./src/CaptainsLog/style.css', './CaptainsLog'),
           ('./src/CaptainsLog/icons', './CaptainsLog'),
           ('./src/CaptainsLog/icons/com.alexdlukens.CaptainsLog.svg', './CaptainsLog/icons')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={
        "gi": {
            "icons": ["Adwaita"],
            "themes": ["Adwaita"],
            "languages": ["en_US"],
            "module-versions": {
                "Gtk": "4.0",
                "GtkSource": "4",
            },
        },
    },
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='CaptainsLog',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
