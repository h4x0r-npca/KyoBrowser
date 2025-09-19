from cx_Freeze import setup, Executable
import sys
import os

# 아이콘 지정 (없으면 None)
icon_path = "kyobrowser.ico" if os.path.exists("kyobrowser.ico") else None

build_exe_options = {
    "packages": ["os", "sys"],
    "includes": ["PySide6", "PySide6.QtWebEngineWidgets"],
    "excludes": [],
    "include_files": [
        ("kyobrowser.ico", "kyobrowser.ico")  # 아이콘, 리소스 포함
    ],
}

setup(
    name="KyoBrowser",
    version="1.0",
    description="Custom Chromium-based Browser",
    options={"build_exe": build_exe_options},
    executables=[
        Executable(
            script="chromium_browser.py",
            base="Win32GUI",  # GUI 앱이면 Win32GUI, 콘솔도 필요하면 Console
            target_name="KyoBrowser.exe",
            icon=icon_path
        )
    ]
)
