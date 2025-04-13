from setuptools import setup

APP = ['viewer_gui.py']  # Ana Python dosyanızın adı
DATA_FILES = []
OPTIONS = {
    'argv_emulation': True,
    'packages': [
        'PyQt6', 'websockets', 'PIL', 'asyncio', 'mss', 'pyautogui', 'hashlib', 'secrets',
        'ssl', 'socket', 'json', 'logging', 'time', 'base64', 'io', 'os', 'hashlib'
    ],
    'includes': ['PyQt6.QtGui', 'PyQt6.QtCore'],  # PyQt6 ile ilgili modülleri dahil edin
    'excludes': ['PySide2', 'PyInstaller'],  # PySide2 ve PyInstaller'ı dışarıda bırakın
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
