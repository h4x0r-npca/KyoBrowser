# Kyo Browser 1.1

Lightweight custom browser built with **PySide6 (QtWebEngine)**.

## Features
- Tabs, favicon
- Download Manager
- Bookmark Manager (separate window, edit/delete)
- Bookmark toolbar
- Custom start page URL
- Bookmark toolbar context menu for edit/delete
- Session restore and recently closed tabs
- Visit history
- Dark/light/system theme
- Zoom controls
- Cache/cookie cleanup
- Settings dialog
- Persistent cookies/storage
- Language interceptor
- About dialog

## Run
```bash
pip install -r requirements.txt
python kyobrowser.py
```

## Build
```bash
pyinstaller kyobrowser.spec
```
