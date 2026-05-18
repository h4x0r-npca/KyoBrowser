import sys
import os
import json
import shutil
from datetime import datetime, timedelta
from urllib.parse import quote_plus

from PySide6.QtCore import QUrl, QSize, Qt, Signal, QEvent, QProcess, QTimer
from PySide6.QtGui import QAction, QDesktopServices, QKeySequence, QIcon, QPalette
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QLineEdit, QToolBar, QFileDialog,
    QLabel, QTabWidget, QDialog, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget, QHBoxLayout, QPushButton,
    QMenu, QToolButton, QMessageBox, QTabBar, QCheckBox,
    QFormLayout, QDialogButtonBox, QComboBox, QSpinBox, QGroupBox,
    QAbstractSpinBox
)
from PySide6.QtWebEngineCore import (
    QWebEngineProfile, QWebEnginePage, QWebEngineDownloadRequest, QWebEngineUrlRequestInterceptor
)
from PySide6.QtWebEngineWidgets import QWebEngineView

# 🖼️ 작업표시줄 AppUserModelID (Windows)
if os.name == "nt":
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Kyo.Browser")

HOME_URL = "https://www.google.com"
APP_VERSION = "1.1"

# ------------------------------------------------------
# 📁 사용자 데이터 폴더 & 북마크 파일
# ------------------------------------------------------
def get_user_data_dir() -> str:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or os.path.expanduser("~")
    path = os.path.join(base, "KyoBrowser")
    os.makedirs(path, exist_ok=True)
    return path

USER_DATA_DIR = get_user_data_dir()
BOOKMARK_FILE = os.path.join(USER_DATA_DIR, "bookmarks.json")
SETTINGS_FILE = os.path.join(USER_DATA_DIR, "settings.json")
SESSION_FILE = os.path.join(USER_DATA_DIR, "session.json")
HISTORY_FILE = os.path.join(USER_DATA_DIR, "history.json")

MAX_RECENT_CLOSED = 20
DEFAULT_ZOOM = 100
MIN_ZOOM = 80
MAX_ZOOM = 200
ZOOM_STEP = 10

DEFAULT_SETTINGS = {
    "restore_session": False,
    "show_bookmarks_toolbar": True,
    "theme": "system",
    "home_url": HOME_URL,
    "default_zoom": DEFAULT_ZOOM,
    "history_retention_days": 90,
}

LIGHT_STYLE = """
QMainWindow, QDialog { background: #f6f7f9; color: #202124; }
QToolBar { background: #ffffff; border: 0; border-bottom: 1px solid #dadce0; spacing: 4px; padding: 4px; }
QLabel, QCheckBox, QGroupBox { color: #202124; }
QGroupBox { border: 1px solid #d5d9df; border-radius: 6px; margin-top: 10px; padding: 10px; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; background: #f6f7f9; color: #202124; }
QLineEdit { background: #ffffff; color: #202124; border: 1px solid #c9cdd3; border-radius: 6px; padding: 6px 8px; }
QLineEdit:focus { border-color: #4f7cff; }
QComboBox, QSpinBox { background: #ffffff; color: #202124; border: 1px solid #c9cdd3; border-radius: 6px; padding: 5px 8px; }
QComboBox QAbstractItemView { background: #ffffff; color: #202124; selection-background-color: #dbe7ff; }
QPushButton, QToolButton { background: #ffffff; color: #202124; border: 1px solid #d5d9df; border-radius: 6px; padding: 5px 8px; }
QToolButton#stepperButton { font-size: 16px; font-weight: 700; min-width: 30px; min-height: 26px; padding: 2px; }
QPushButton:hover, QToolButton:hover { background: #eef3ff; border-color: #9db8ff; }
QPushButton:disabled, QToolButton:disabled { color: #9aa0a6; background: #f1f3f4; }
QTabWidget::pane { border: 0; }
QTabBar::tab { background: #e9edf3; color: #202124; padding: 7px 14px; border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 2px; }
QTabBar::tab:selected { background: #ffffff; }
QTableWidget { background: #ffffff; color: #202124; gridline-color: #e5e7eb; selection-background-color: #dbe7ff; }
QHeaderView::section { background: #eef1f5; color: #202124; padding: 5px; border: 0; border-right: 1px solid #d5d9df; }
QMenu { background: #ffffff; color: #202124; border: 1px solid #dadce0; }
QMenu::item:selected { background: #eef3ff; }
"""

DARK_STYLE = """
QMainWindow, QDialog { background: #1f2329; color: #e8eaed; }
QToolBar { background: #262b33; border: 0; border-bottom: 1px solid #343a45; spacing: 4px; padding: 4px; }
QLabel, QCheckBox, QGroupBox { color: #e8eaed; }
QGroupBox { border: 1px solid #4a5260; border-radius: 6px; margin-top: 10px; padding: 10px; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; background: #1f2329; color: #e8eaed; }
QLineEdit { background: #15191f; color: #e8eaed; border: 1px solid #4a5260; border-radius: 6px; padding: 6px 8px; }
QLineEdit:focus { border-color: #7ea1ff; }
QComboBox, QSpinBox { background: #15191f; color: #e8eaed; border: 1px solid #4a5260; border-radius: 6px; padding: 5px 8px; }
QComboBox QAbstractItemView { background: #252a31; color: #e8eaed; selection-background-color: #35476a; }
QPushButton, QToolButton { background: #2d333d; color: #e8eaed; border: 1px solid #4a5260; border-radius: 6px; padding: 5px 8px; }
QToolButton#stepperButton { font-size: 16px; font-weight: 700; min-width: 30px; min-height: 26px; padding: 2px; }
QPushButton:hover, QToolButton:hover { background: #384154; border-color: #6f8fe8; }
QPushButton:disabled, QToolButton:disabled { color: #707783; background: #252a31; }
QTabWidget::pane { border: 0; }
QTabBar::tab { background: #2b313b; color: #cfd4dc; padding: 7px 14px; border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 2px; }
QTabBar::tab:selected { background: #1f2329; color: #ffffff; }
QTableWidget { background: #15191f; color: #e8eaed; gridline-color: #343a45; selection-background-color: #35476a; }
QHeaderView::section { background: #2b313b; color: #e8eaed; padding: 5px; border: 0; border-right: 1px solid #343a45; }
QMenu { background: #252a31; color: #e8eaed; border: 1px solid #343a45; }
QMenu::item:selected { background: #35476a; }
"""

# (선택) 구버전 bookmarks.json 자동 마이그레이션
try:
    legacy_bm = os.path.join(os.getcwd(), "bookmarks.json")
    if os.path.exists(legacy_bm) and not os.path.exists(BOOKMARK_FILE):
        shutil.copy2(legacy_bm, BOOKMARK_FILE)
except Exception:
    pass

def resource_path(name: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, name)

def _copy_default(default):
    if isinstance(default, dict):
        return dict(default)
    if isinstance(default, list):
        return list(default)
    return default

def load_json_file(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(default, dict) and isinstance(data, dict):
                    merged = dict(default)
                    merged.update(data)
                    return merged
                if isinstance(default, list) and isinstance(data, list):
                    return data
        except Exception:
            pass
    return _copy_default(default)

def save_json_file(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def now_iso():
    return datetime.now().isoformat(timespec="seconds")

def normalize_url(url):
    return url.toString() if isinstance(url, QUrl) else str(url or "")

def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))

def to_int(value, default):
    try:
        return int(value)
    except Exception:
        return default

def configure_chromium_flags():
    flags = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "")
    disable_features = "CompressionDictionaryTransport,CompressionDictionaryTransportBackend"
    flag = f"--disable-features={disable_features}"
    if disable_features not in flags:
        os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = f"{flags} {flag}".strip()

# ------------------------------------------------------
# 🖱️ 가운데 클릭으로 탭 닫기 지원 탭바
# ------------------------------------------------------
class CloseOnMiddleClickTabBar(QTabBar):
    middleClickClose = Signal(int)
    plusTabClicked = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._suppress_next_left_release = False

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            idx = self.tabAt(e.pos())
            if idx != -1 and self.tabText(idx) == "+":
                self._suppress_next_left_release = True
                self.plusTabClicked.emit(idx)
                e.accept()
                return
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self._suppress_next_left_release:
            self._suppress_next_left_release = False
            e.accept()
            return
        if e.button() == Qt.MiddleButton:
            idx = self.tabAt(e.pos())
            if idx != -1:
                self.middleClickClose.emit(idx)
                e.accept()
                return
        super().mouseReleaseEvent(e)

# ------------------------------------------------------
# 🌐 요청 인터셉터 (Accept-Language)
# ------------------------------------------------------
class MyInterceptor(QWebEngineUrlRequestInterceptor):
    def interceptRequest(self, info):
        info.setHttpHeader(b"Accept-Language", b"ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7")

# ------------------------------------------------------
# 📥 다운로드 관리자
# ------------------------------------------------------
class DownloadManager(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("다운로드 관리자")
        self.resize(640, 320)

        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 5, self)
        self.table.setHorizontalHeaderLabels(["파일명", "크기", "진행률", "상태", "액션"])
        layout.addWidget(self.table)

        self.downloads = []

        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)

    def add_download(self, download_item: QWebEngineDownloadRequest):
        for d in self.downloads:
            if d["item"] == download_item:
                print("이미 추가된 다운로드 항목입니다.")
                return

        row = self.table.rowCount()
        self.table.insertRow(row)

        filename = download_item.downloadFileName() or download_item.suggestedFileName() or "download"
        self.table.setItem(row, 0, QTableWidgetItem(filename))
        self.table.setItem(row, 1, QTableWidgetItem("알 수 없음"))
        self.table.setItem(row, 2, QTableWidgetItem("0%"))
        self.table.setItem(row, 3, QTableWidgetItem("다운로드 중"))

        action_widget = QWidget()
        h = QHBoxLayout(action_widget)
        h.setContentsMargins(0, 0, 0, 0)

        btn_cancel = QPushButton("취소")
        btn_open = QPushButton("열기")
        btn_folder = QPushButton("폴더")
        btn_open.setEnabled(False)
        btn_folder.setEnabled(False)

        h.addWidget(btn_cancel)
        h.addWidget(btn_open)
        h.addWidget(btn_folder)
        self.table.setCellWidget(row, 4, action_widget)

        info = {
            "item": download_item,
            "row": row,
            "filename": filename,
            "btn_cancel": btn_cancel,
            "btn_open": btn_open,
            "btn_folder": btn_folder,
        }
        self.downloads.append(info)

        btn_cancel.clicked.connect(lambda: self.cancel_download(info))
        btn_open.clicked.connect(lambda: self.open_download(info))
        btn_folder.clicked.connect(lambda: self.open_download_folder(info))

        download_item.receivedBytesChanged.connect(lambda: self.update_progress(info))
        download_item.stateChanged.connect(lambda s: self.on_state_changed(info, s))

        if not self.isVisible():
            self.show()

    def update_progress(self, info):
        item = info["item"]
        rcv = item.receivedBytes()
        tot = item.totalBytes()

        if tot > 0:
            pct = int((rcv / tot) * 100)
            self.table.setItem(info["row"], 2, QTableWidgetItem(f"{pct}%"))
            self.table.setItem(info["row"], 1, QTableWidgetItem(f"{rcv:,} / {tot:,} bytes"))
        else:
            self.table.setItem(info["row"], 1, QTableWidgetItem(f"{rcv:,} bytes"))
            self.table.setItem(info["row"], 2, QTableWidgetItem("진행 중…"))

    def on_state_changed(self, info, state):
        if state == QWebEngineDownloadRequest.DownloadCompleted:
            fp = self._download_path(info)
            if os.path.exists(fp):
                self.mark_finished(info)
            else:
                self.table.setItem(info["row"], 3, QTableWidgetItem("오류"))
                info["btn_cancel"].setEnabled(False)
                info["btn_open"].setEnabled(False)
        elif state == QWebEngineDownloadRequest.DownloadCancelled:
            self.table.setItem(info["row"], 3, QTableWidgetItem("취소됨"))
            info["btn_cancel"].setEnabled(False)
            info["btn_open"].setEnabled(False)
        elif state == QWebEngineDownloadRequest.DownloadInterrupted:
            self.table.setItem(info["row"], 3, QTableWidgetItem("중단됨"))
            info["btn_cancel"].setEnabled(False)
            info["btn_open"].setEnabled(False)

    def mark_finished(self, info):
        self.table.setItem(info["row"], 3, QTableWidgetItem("완료"))
        info["btn_open"].setEnabled(True)
        info["btn_folder"].setEnabled(True)
        info["btn_cancel"].setText("삭제")
        try:
            info["btn_cancel"].clicked.disconnect()
        except Exception:
            pass
        info["btn_cancel"].clicked.connect(lambda: self.remove_download(info))

    def cancel_download(self, info):
        info["item"].cancel()

    def open_download(self, info):
        fp = self._download_path(info)
        if os.path.exists(fp):
            QDesktopServices.openUrl(QUrl.fromLocalFile(fp))
        else:
            QMessageBox.warning(self, "오류", "파일을 찾을 수 없습니다.")

    def open_download_folder(self, info):
        dir_ = os.path.normpath(os.path.abspath(info["item"].downloadDirectory() or ""))
        fp = self._download_path(info)
        if not os.path.isdir(dir_):
            QMessageBox.warning(self, "오류", "다운로드 폴더를 찾을 수 없습니다.")
            return

        if os.name == "nt":
            try:
                if os.path.exists(fp):
                    QProcess.startDetached("explorer", ["/select,", fp])
                else:
                    QProcess.startDetached("explorer", [dir_])
            except Exception:
                QDesktopServices.openUrl(QUrl.fromLocalFile(dir_))
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(dir_))

    def remove_download(self, info):
        row = info["row"]
        self.table.removeRow(row)
        self.downloads.remove(info)
        for d in self.downloads:
            if d["row"] > row:
                d["row"] -= 1

    def _download_path(self, info):
        item = info["item"]
        filename = item.downloadFileName() or info["filename"]
        return os.path.join(item.downloadDirectory(), filename)

# ------------------------------------------------------
# ⭐ 즐겨찾기 관리자 (별도 다이얼로그)
# ------------------------------------------------------
class BookmarkManager(QDialog):
    def __init__(self, browser, parent=None):
        super().__init__(parent)
        self.browser = browser
        self.setWindowTitle("즐겨찾기 관리자")
        self.resize(720, 320)

        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 3, self)
        self.table.setHorizontalHeaderLabels(["제목", "URL", "액션"])
        layout.addWidget(self.table)

        self.refresh()

    def refresh(self):
        self.table.setRowCount(0)
        for idx, bm in enumerate(self.browser.bookmarks):
            row = self.table.rowCount()
            self.table.insertRow(row)

            self.table.setItem(row, 0, QTableWidgetItem(bm.get("title", "")))
            self.table.setItem(row, 1, QTableWidgetItem(bm.get("url", "")))

            btn_open = QPushButton("열기")
            btn_edit = QPushButton("편집")
            btn_delete = QPushButton("삭제")

            action_widget = QWidget()
            h = QHBoxLayout(action_widget)
            h.setContentsMargins(0, 0, 0, 0)
            h.addWidget(btn_open)
            h.addWidget(btn_edit)
            h.addWidget(btn_delete)
            self.table.setCellWidget(row, 2, action_widget)

            btn_open.clicked.connect(lambda _=False, url=bm["url"]: self.browser.create_new_tab(url))
            btn_edit.clicked.connect(lambda _=False, i=idx: self.edit_bookmark(i))
            btn_delete.clicked.connect(lambda _=False, i=idx: self.delete_bookmark(i))

    def delete_bookmark(self, index: int):
        self.browser.delete_bookmark(index)
        self.refresh()

    def edit_bookmark(self, index: int):
        self.browser.edit_bookmark(index)
        self.refresh()

# ------------------------------------------------------
# 🌍 WebView (탭에 올라가는 실제 브라우저 뷰)
# ------------------------------------------------------
class WebView(QWebEngineView):
    def __init__(self, profile, browser, parent=None):
        super().__init__(parent)
        self.browser = browser
        self.setPage(QWebEnginePage(profile, self))

    def createWindow(self, _type):
        return self.browser.create_new_tab(self.browser.get_home_url())

# ------------------------------------------------------
# ℹ️ About 다이얼로그
# ------------------------------------------------------
class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About Kyo Browser")
        self.resize(460, 300)

        layout = QVBoxLayout(self)
        label = QLabel(
            f"""
            <h2>Kyo Browser {APP_VERSION}</h2>
            <p>답답함을 해결하기 위해 직접 만든 브라우저</p>
            <p>세션 복원, 방문 기록, 즐겨찾기 툴바, 테마, 확대/축소, 개인정보 정리 기능을 포함합니다.</p>
            <p><b>E-mail:</b> dersertfox@kakao.com</p>
            <hr>
            <p>Developed by <b>Kyo</b></p>
            <p>Powered by <b>PySide6 / QtWebEngine</b></p>
            <p style="font-size:10px; color:gray;">
                © 2026 Kyo. All rights reserved.
            </p>
            """
        )
        label.setAlignment(Qt.AlignCenter)
        label.setWordWrap(True)
        layout.addWidget(label)

        btn = QPushButton("닫기")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn, alignment=Qt.AlignCenter)

# ------------------------------------------------------
# ⌨️ 단축키 일러두기
# ------------------------------------------------------
class ShortcutsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("단축키 일러두기")
        self.resize(520, 340)

        layout = QVBoxLayout(self)
        table = QTableWidget(self)
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["동작", "단축키"])
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)

        data = [
            ("주소창 포커스", "Ctrl + L"),
            ("새 탭", "Ctrl + T"),
            ("현재 탭 닫기", "Ctrl + W"),
            ("즐겨찾기 추가", "Ctrl + D"),
            ("찾기 열기", "Ctrl + F"),
            ("최근 닫은 탭 다시 열기", "Ctrl + Shift + T"),
            ("확대", "Ctrl + +"),
            ("축소", "Ctrl + -"),
            ("확대율 초기화", "Ctrl + 0"),
            ("찾기: 다음 결과", "Enter (검색창 포커스 중)"),
            ("찾기: 이전 결과", "Shift + Enter (검색창 포커스 중)"),
            ("찾기 닫기", "Esc (검색창 포커스 중)"),
            ("탭 닫기", "마우스 가운데 버튼(휠) 클릭"),
            ("새 탭", "탭바의 [+] 클릭"),
        ]

        table.setRowCount(len(data))
        for r, (action, keys) in enumerate(data):
            table.setItem(r, 0, QTableWidgetItem(action))
            table.setItem(r, 1, QTableWidgetItem(keys))

        table.resizeColumnsToContents()
        layout.addWidget(table)

        btns = QDialogButtonBox(QDialogButtonBox.Close)
        for b in btns.buttons():
            b.clicked.connect(self.accept)
        layout.addWidget(btns)

class HistoryDialog(QDialog):
    def __init__(self, browser, parent=None):
        super().__init__(parent)
        self.browser = browser
        self.setWindowTitle("방문 기록")
        self.resize(860, 420)

        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 3, self)
        self.table.setHorizontalHeaderLabels(["방문 시각", "제목", "URL"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.cellDoubleClicked.connect(lambda _r, _c: self.open_selected())
        layout.addWidget(self.table)

        button_row = QHBoxLayout()
        btn_open = QPushButton("열기")
        btn_delete = QPushButton("삭제")
        btn_clear = QPushButton("전체 삭제")
        btn_close = QPushButton("닫기")
        btn_open.clicked.connect(self.open_selected)
        btn_delete.clicked.connect(self.delete_selected)
        btn_clear.clicked.connect(self.clear_all)
        btn_close.clicked.connect(self.accept)
        button_row.addWidget(btn_open)
        button_row.addWidget(btn_delete)
        button_row.addWidget(btn_clear)
        button_row.addStretch(1)
        button_row.addWidget(btn_close)
        layout.addLayout(button_row)

        self.refresh()

    def refresh(self):
        self.table.setRowCount(0)
        self.browser._prune_history(save=True)
        for idx, item in enumerate(self.browser.history):
            row = self.table.rowCount()
            self.table.insertRow(row)

            visited = QTableWidgetItem(item.get("visited_at", ""))
            visited.setData(Qt.UserRole, idx)
            self.table.setItem(row, 0, visited)
            self.table.setItem(row, 1, QTableWidgetItem(item.get("title", "")))
            self.table.setItem(row, 2, QTableWidgetItem(item.get("url", "")))

        self.table.resizeColumnsToContents()

    def _selected_index(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def open_selected(self):
        idx = self._selected_index()
        if idx is None or not (0 <= idx < len(self.browser.history)):
            return
        url = self.browser.history[idx].get("url", "")
        if url:
            self.browser.create_new_tab(url)

    def delete_selected(self):
        idx = self._selected_index()
        if idx is None:
            return
        self.browser.delete_history_item(idx)
        self.refresh()

    def clear_all(self):
        if QMessageBox.question(self, "방문 기록", "방문 기록을 모두 삭제할까요?") == QMessageBox.Yes:
            self.browser.clear_history()
            self.refresh()

class SettingsDialog(QDialog):
    THEME_OPTIONS = [
        ("system", "시스템 기준"),
        ("light", "라이트"),
        ("dark", "다크"),
    ]

    def __init__(self, browser, parent=None):
        super().__init__(parent)
        self.browser = browser
        self.setWindowTitle("환경설정")
        self.resize(520, 420)

        layout = QVBoxLayout(self)

        general_group = QGroupBox("일반")
        form = QFormLayout(general_group)

        self.restore_session = QCheckBox("이전 세션 복원")
        self.restore_session.setChecked(bool(browser.settings.get("restore_session", False)))
        form.addRow("시작:", self.restore_session)

        self.home_url = QLineEdit(browser.get_home_url())
        self.home_url.setPlaceholderText(HOME_URL)
        form.addRow("시작페이지 URL:", self.home_url)

        self.show_bookmarks_toolbar = QCheckBox("즐겨찾기 툴바 표시")
        self.show_bookmarks_toolbar.setChecked(bool(browser.settings.get("show_bookmarks_toolbar", True)))
        form.addRow("즐겨찾기:", self.show_bookmarks_toolbar)

        self.theme_combo = QComboBox()
        for value, label in self.THEME_OPTIONS:
            self.theme_combo.addItem(label, value)
        theme = browser.settings.get("theme", "system")
        self.theme_combo.setCurrentIndex(max(0, self.theme_combo.findData(theme)))
        form.addRow("테마:", self.theme_combo)

        self.default_zoom = QSpinBox()
        self.default_zoom.setRange(MIN_ZOOM, MAX_ZOOM)
        self.default_zoom.setSingleStep(ZOOM_STEP)
        self.default_zoom.setSuffix("%")
        self.default_zoom.setValue(int(browser.settings.get("default_zoom", DEFAULT_ZOOM)))
        form.addRow("기본 확대율:", self._build_stepper(self.default_zoom, "확대율 낮추기", "확대율 높이기"))

        self.history_days = QSpinBox()
        self.history_days.setRange(1, 3650)
        self.history_days.setSingleStep(1)
        self.history_days.setSuffix("일")
        self.history_days.setValue(int(browser.settings.get("history_retention_days", 90)))
        form.addRow("기록 보관:", self._build_stepper(self.history_days, "보관 기간 줄이기", "보관 기간 늘리기"))

        layout.addWidget(general_group)

        privacy_group = QGroupBox("개인정보")
        privacy_row = QHBoxLayout(privacy_group)
        btn_cache = QPushButton("캐시 삭제")
        btn_cookies = QPushButton("쿠키 삭제")
        btn_history = QPushButton("기록 삭제")
        btn_session = QPushButton("세션 삭제")
        btn_cache.clicked.connect(browser.clear_cache)
        btn_cookies.clicked.connect(browser.clear_cookies)
        btn_history.clicked.connect(self._clear_history)
        btn_session.clicked.connect(browser.clear_saved_session)
        privacy_row.addWidget(btn_cache)
        privacy_row.addWidget(btn_cookies)
        privacy_row.addWidget(btn_history)
        privacy_row.addWidget(btn_session)
        layout.addWidget(privacy_group)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Apply | QDialogButtonBox.Cancel)
        self.apply_button = buttons.button(QDialogButtonBox.Apply)
        if self.apply_button:
            self.apply_button.setText("적용")
            self.apply_button.clicked.connect(self.apply_changes)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _clear_history(self):
        if QMessageBox.question(self, "방문 기록", "방문 기록을 모두 삭제할까요?") == QMessageBox.Yes:
            self.browser.clear_history()

    def _build_stepper(self, spinbox, minus_tooltip, plus_tooltip):
        spinbox.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        spinbox.setAlignment(Qt.AlignCenter)
        spinbox.setMinimumWidth(96)

        container = QWidget(self)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        btn_minus = QToolButton(container)
        btn_minus.setObjectName("stepperButton")
        btn_minus.setText("-")
        btn_minus.setToolTip(minus_tooltip)
        btn_minus.clicked.connect(spinbox.stepDown)

        btn_plus = QToolButton(container)
        btn_plus.setObjectName("stepperButton")
        btn_plus.setText("+")
        btn_plus.setToolTip(plus_tooltip)
        btn_plus.clicked.connect(spinbox.stepUp)

        layout.addWidget(btn_minus)
        layout.addWidget(spinbox, 1)
        layout.addWidget(btn_plus)
        return container

    def apply_changes(self):
        self.browser.apply_settings(self.values())

    def values(self):
        return {
            "restore_session": self.restore_session.isChecked(),
            "show_bookmarks_toolbar": self.show_bookmarks_toolbar.isChecked(),
            "theme": self.theme_combo.currentData(),
            "home_url": self.home_url.text().strip(),
            "default_zoom": self.default_zoom.value(),
            "history_retention_days": self.history_days.value(),
        }

# ------------------------------------------------------
# 🧭 메인 브라우저 윈도우
# ------------------------------------------------------
class Browser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kyo's Browser")
        self.resize(1200, 800)

        # 아이콘
        icon = None
        try:
            icon_path = resource_path("kyobrowser.ico")
            if os.path.exists(icon_path):
                icon = QIcon(icon_path)
            elif os.path.exists("kyobrowser.ico"):
                icon = QIcon("kyobrowser.ico")
        except Exception:
            pass
        self.setWindowIcon(icon or QIcon())

        self.settings = self._load_settings()
        self.history = self._load_history()
        self._prune_history(save=True)
        self.saved_session = self._load_session()
        self.recent_closed_tabs = self.saved_session.get("recent_closed", [])
        self._closing_app = False
        self._skip_next_session_save = False
        self.history_dialog = None

        # 프로필 (쿠키/캐시/저장소 경로 고정)
        storage_path = os.path.join(USER_DATA_DIR, "browser_data")
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)
        self._cleanup_shared_dictionary_store(storage_path)

        self.profile = QWebEngineProfile("KyoProfile")
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.ForcePersistentCookies)
        self.profile.setCachePath(os.path.join(storage_path, "cache"))
        self.profile.setPersistentStoragePath(os.path.join(storage_path, "storage"))
        self.profile.setHttpUserAgent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        )
        self.interceptor = MyInterceptor()
        self.profile.setUrlRequestInterceptor(self.interceptor)
        self.profile.downloadRequested.connect(self.on_download_requested)

        # 탭 위젯
        self.tabs = QTabWidget()
        midclose_tabbar = CloseOnMiddleClickTabBar(self.tabs)
        midclose_tabbar.middleClickClose.connect(self.close_tab)
        midclose_tabbar.plusTabClicked.connect(self._open_tab_from_plus)
        self.tabs.setTabBar(midclose_tabbar)
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.setDocumentMode(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        # currentChanged는 우리가 직접 핸들(“+” 탭 포함)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.setCentralWidget(self.tabs)

        # 주소창
        self.location_bar = QLineEdit(self)
        self.location_bar.setClearButtonEnabled(True)
        self.location_bar.returnPressed.connect(self.load_from_location)

        # 상태바
        self.status_label = QLabel("")
        self.statusBar().addPermanentWidget(self.status_label)

        # 데이터/매니저
        self.bookmarks = self._load_bookmarks()
        self.download_manager = DownloadManager(self)
        self.bookmark_manager = BookmarkManager(self, self)

        # 가드 플래그: 탭 닫는 동안 + 탭 자동생성 방지
        self._ignore_plus_click = False

        # 툴바/단축키/초기 탭
        self._build_toolbar()
        if not self._restore_session():
            self.create_new_tab(self.get_home_url())   # 첫 실제 탭
        self._ensure_plus_tab()         # 항상 맨 끝에 “+” 더미 탭 유지
        self._setup_shortcuts()
        self._update_star()
        self._update_zoom_label()

        # 🔍 찾기 툴바
        self.find_bar = QLineEdit(self)
        self.find_bar.setPlaceholderText("검색어 입력 후 Enter…")
        self.find_bar.returnPressed.connect(self._find_from_enter)
        self.find_bar.installEventFilter(self)

        self.chk_case = QCheckBox("Aa", self)
        self.chk_case.setToolTip("대소문자 구분")

        self.btn_prev = QToolButton(self)
        self.btn_prev.setText("⬆")
        self.btn_prev.setToolTip("이전 검색(Shift+Enter)")
        self.btn_prev.clicked.connect(self._find_prev)

        self.btn_next = QToolButton(self)
        self.btn_next.setText("⬇")
        self.btn_next.setToolTip("다음 검색(Enter)")
        self.btn_next.clicked.connect(self._find_next)

        self.btn_close_find = QToolButton(self)
        self.btn_close_find.setText("✕")
        self.btn_close_find.setToolTip("검색 닫기 (Esc)")
        self.btn_close_find.clicked.connect(self._close_find)

        self.addToolBarBreak()
        find_tb = QToolBar("Find", self)
        find_tb.addWidget(QLabel("찾기: ", self))
        find_tb.addWidget(self.find_bar)
        find_tb.addWidget(self.chk_case)
        find_tb.addWidget(self.btn_prev)
        find_tb.addWidget(self.btn_next)
        find_tb.addWidget(self.btn_close_find)
        self.addToolBar(Qt.BottomToolBarArea, find_tb)
        self.find_tb = find_tb
        self.find_tb.hide()
        self.apply_theme()

    # ---------------- Persistent data helpers ----------------
    def _load_settings(self):
        settings = load_json_file(SETTINGS_FILE, DEFAULT_SETTINGS)
        settings["theme"] = settings.get("theme") if settings.get("theme") in {"system", "light", "dark"} else "system"
        settings["home_url"] = self._normalize_home_url(settings.get("home_url", HOME_URL))
        settings["default_zoom"] = clamp(to_int(settings.get("default_zoom", DEFAULT_ZOOM), DEFAULT_ZOOM), MIN_ZOOM, MAX_ZOOM)
        settings["history_retention_days"] = max(1, to_int(settings.get("history_retention_days", 90), 90))
        settings["restore_session"] = bool(settings.get("restore_session", False))
        settings["show_bookmarks_toolbar"] = bool(settings.get("show_bookmarks_toolbar", True))
        return settings

    def _normalize_home_url(self, text):
        text = str(text or "").strip()
        if not text:
            return HOME_URL
        if "://" in text:
            return text
        return "http://" + text

    def get_home_url(self):
        return self._normalize_home_url(self.settings.get("home_url", HOME_URL))

    def _save_settings(self):
        save_json_file(SETTINGS_FILE, self.settings)

    def _load_session(self):
        data = load_json_file(SESSION_FILE, {"tabs": [], "current_index": 0, "recent_closed": []})
        data["tabs"] = data.get("tabs", []) if isinstance(data.get("tabs", []), list) else []
        data["recent_closed"] = data.get("recent_closed", []) if isinstance(data.get("recent_closed", []), list) else []
        data["current_index"] = to_int(data.get("current_index", 0), 0)
        return data

    def _load_history(self):
        return load_json_file(HISTORY_FILE, [])

    def _cleanup_shared_dictionary_store(self, storage_path):
        root = os.path.abspath(storage_path)
        if not os.path.isdir(root):
            return

        targets = []
        for current, dirs, files in os.walk(root):
            for name in dirs + files:
                lowered = name.lower().replace("-", "_")
                if "shared dictionary" in lowered or "shared_dictionary" in lowered:
                    targets.append(os.path.join(current, name))

        for target in sorted(targets, key=len, reverse=True):
            abs_target = os.path.abspath(target)
            if not abs_target.startswith(root):
                continue
            try:
                if os.path.isdir(abs_target):
                    shutil.rmtree(abs_target)
                elif os.path.exists(abs_target):
                    os.remove(abs_target)
            except Exception:
                pass

    def _save_history(self):
        save_json_file(HISTORY_FILE, self.history)

    def _prune_history(self, save=False):
        days = to_int(self.settings.get("history_retention_days", 90), 90)
        cutoff = datetime.now() - timedelta(days=days)
        kept = []
        for item in self.history:
            try:
                visited_at = datetime.fromisoformat(item.get("visited_at", ""))
            except Exception:
                continue
            if visited_at >= cutoff:
                kept.append(item)
        if len(kept) != len(self.history):
            self.history = kept
            if save:
                self._save_history()

    # ---------------- Bookmark helpers ----------------
    def _load_bookmarks(self):
        return load_json_file(BOOKMARK_FILE, [])

    def _save_bookmarks(self):
        save_json_file(BOOKMARK_FILE, self.bookmarks)
        if hasattr(self, "bookmark_toolbar"):
            self._refresh_bookmarks_toolbar()

    def _is_bookmarked(self, url: str) -> bool:
        return any(bm.get("url") == url for bm in self.bookmarks)

    def _remove_bookmark_by_url(self, url: str):
        before = len(self.bookmarks)
        self.bookmarks = [bm for bm in self.bookmarks if bm.get("url") != url]
        if len(self.bookmarks) != before:
            self._save_bookmarks()
            self.bookmark_manager.refresh()

    def edit_bookmark(self, index: int):
        if not (0 <= index < len(self.bookmarks)):
            return

        bm = self.bookmarks[index]
        dialog = QDialog(self)
        dialog.setWindowTitle("즐겨찾기 편집")
        form = QFormLayout(dialog)

        title_edit = QLineEdit(bm.get("title", ""))
        url_edit = QLineEdit(bm.get("url", ""))

        form.addRow("제목:", title_edit)
        form.addRow("URL:", url_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        form.addWidget(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        if dialog.exec() == QDialog.Accepted:
            new_title = title_edit.text().strip()
            new_url = url_edit.text().strip()
            if new_title and new_url:
                bm["title"] = new_title
                bm["url"] = self._normalize_home_url(new_url)
                self._save_bookmarks()
                self.bookmark_manager.refresh()
                self._update_star()

    def delete_bookmark(self, index: int, confirm=False):
        if not (0 <= index < len(self.bookmarks)):
            return
        if confirm:
            title = self.bookmarks[index].get("title") or self.bookmarks[index].get("url") or "선택한 항목"
            if QMessageBox.question(self, "즐겨찾기 삭제", f"'{title}' 즐겨찾기를 삭제할까요?") != QMessageBox.Yes:
                return
        del self.bookmarks[index]
        self._save_bookmarks()
        self.bookmark_manager.refresh()
        self._update_star()

    def _update_star(self):
        view = self.current_view()
        url = view.url().toString() if view else ""
        if hasattr(self, "star_btn"):
            if url and self._is_bookmarked(url):
                self.star_btn.setText("★")
                self.star_btn.setToolTip("즐겨찾기 제거")
            else:
                self.star_btn.setText("☆")
                self.star_btn.setToolTip("즐겨찾기 추가 (Ctrl+D)")

    def _refresh_bookmarks_toolbar(self):
        if not hasattr(self, "bookmark_toolbar"):
            return
        self.bookmark_toolbar.clear()
        self.bookmark_toolbar.setVisible(bool(self.settings.get("show_bookmarks_toolbar", True)))
        for idx, bm in enumerate(self.bookmarks):
            title = bm.get("title") or bm.get("url") or "무제"
            url = bm.get("url", "")
            if not url:
                continue
            action = QAction(title[:28], self)
            action.setToolTip(url)
            action.setData(idx)
            action.triggered.connect(lambda _=False, u=url: self.create_new_tab(u))
            self.bookmark_toolbar.addAction(action)

    def _show_bookmark_context_menu(self, pos):
        action = self.bookmark_toolbar.actionAt(pos)
        if not action:
            return
        index = action.data()
        if not isinstance(index, int) or not (0 <= index < len(self.bookmarks)):
            return

        menu = QMenu(self.bookmark_toolbar)
        act_edit = QAction("수정", self)
        act_delete = QAction("삭제", self)
        act_edit.triggered.connect(lambda _=False, i=index: self.edit_bookmark(i))
        act_delete.triggered.connect(lambda _=False, i=index: self.delete_bookmark(i, confirm=True))
        menu.addAction(act_edit)
        menu.addAction(act_delete)
        menu.exec(self.bookmark_toolbar.mapToGlobal(pos))

    # ---------------- Toolbar ----------------
    def _build_toolbar(self):
        tb = QToolBar("Navigation", self)
        tb.setIconSize(QSize(18, 18))
        self.addToolBar(tb)

        back_action = QAction("◀", self)
        back_action.triggered.connect(lambda _=False: self._run_on_current_view(lambda view: view.back()))
        tb.addAction(back_action)

        fwd_action = QAction("▶", self)
        fwd_action.triggered.connect(lambda _=False: self._run_on_current_view(lambda view: view.forward()))
        tb.addAction(fwd_action)

        reload_action = QAction("🔄", self)
        reload_action.triggered.connect(lambda _=False: self._run_on_current_view(lambda view: view.reload()))
        tb.addAction(reload_action)

        home_action = QAction("🏠", self)
        home_action.triggered.connect(lambda _=False: self._run_on_current_view(lambda view: view.setUrl(QUrl(self.get_home_url()))))
        tb.addAction(home_action)

        tb.addSeparator()
        tb.addWidget(self.location_bar)

        self.star_btn = QToolButton(self)
        self.star_btn.setText("☆")
        self.star_btn.setToolTip("즐겨찾기 추가 (Ctrl+D)")
        self.star_btn.clicked.connect(self.toggle_bookmark_current)
        tb.addWidget(self.star_btn)

        tb.addSeparator()
        menu_button = QToolButton(self)
        menu_button.setText("☰")
        menu_button.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(menu_button)

        act_restore_closed = QAction("최근 닫은 탭 다시 열기", self)
        act_restore_closed.triggered.connect(self.restore_recent_closed_tab)
        menu.addAction(act_restore_closed)

        act_history = QAction("방문 기록", self)
        act_history.triggered.connect(self.show_history)
        menu.addAction(act_history)

        act_downloads = QAction("다운로드 관리자", self)
        act_downloads.triggered.connect(lambda: self.download_manager.show())
        menu.addAction(act_downloads)

        act_bookmarks = QAction("즐겨찾기 관리자", self)
        act_bookmarks.triggered.connect(lambda: self.bookmark_manager.show())
        menu.addAction(act_bookmarks)

        menu.addSeparator()

        self.zoom_status_action = QAction("확대율: 100%", self)
        self.zoom_status_action.setEnabled(False)
        menu.addAction(self.zoom_status_action)

        act_zoom_in = QAction("확대", self)
        act_zoom_in.triggered.connect(self.zoom_in)
        menu.addAction(act_zoom_in)

        act_zoom_out = QAction("축소", self)
        act_zoom_out.triggered.connect(self.zoom_out)
        menu.addAction(act_zoom_out)

        act_zoom_reset = QAction("확대율 초기화", self)
        act_zoom_reset.triggered.connect(self.reset_zoom)
        menu.addAction(act_zoom_reset)

        menu.addSeparator()

        act_settings = QAction("환경설정", self)
        act_settings.triggered.connect(self.show_settings)
        menu.addAction(act_settings)

        act_shortcuts = QAction("단축키 일러두기", self)
        act_shortcuts.triggered.connect(self.show_shortcuts)
        menu.addAction(act_shortcuts)

        act_about = QAction("About", self)
        act_about.triggered.connect(lambda: AboutDialog(self).exec())
        menu.addAction(act_about)

        menu_button.setMenu(menu)
        tb.addWidget(menu_button)

        self.bookmark_toolbar = QToolBar("Bookmarks", self)
        self.bookmark_toolbar.setIconSize(QSize(16, 16))
        self.bookmark_toolbar.setContextMenuPolicy(Qt.CustomContextMenu)
        self.bookmark_toolbar.customContextMenuRequested.connect(self._show_bookmark_context_menu)
        self.addToolBarBreak()
        self.addToolBar(self.bookmark_toolbar)
        self._refresh_bookmarks_toolbar()

    # ---------------- Shortcuts ----------------
    def _setup_shortcuts(self):
        act_focus_url = QAction(self)
        act_focus_url.setShortcut(QKeySequence("Ctrl+L"))
        act_focus_url.triggered.connect(lambda: (self.location_bar.setFocus(), self.location_bar.selectAll()))
        self.addAction(act_focus_url)

        act_new_tab = QAction(self)
        act_new_tab.setShortcut(QKeySequence("Ctrl+T"))
        act_new_tab.triggered.connect(lambda: self.create_new_tab(self.get_home_url()))
        self.addAction(act_new_tab)

        act_close_tab = QAction(self)
        act_close_tab.setShortcut("Ctrl+W")
        act_close_tab.triggered.connect(lambda: self.close_tab(self.tabs.currentIndex()))
        self.addAction(act_close_tab)

        act_bookmark = QAction(self)
        act_bookmark.setShortcut("Ctrl+D")
        act_bookmark.triggered.connect(self.add_bookmark)
        self.addAction(act_bookmark)

        act_find = QAction(self)
        act_find.setShortcut("Ctrl+F")
        act_find.triggered.connect(self.show_find_bar)
        self.addAction(act_find)

        act_restore_tab = QAction(self)
        act_restore_tab.setShortcut("Ctrl+Shift+T")
        act_restore_tab.triggered.connect(self.restore_recent_closed_tab)
        self.addAction(act_restore_tab)

        act_zoom_in = QAction(self)
        act_zoom_in.setShortcuts([QKeySequence("Ctrl++"), QKeySequence("Ctrl+=")])
        act_zoom_in.triggered.connect(self.zoom_in)
        self.addAction(act_zoom_in)

        act_zoom_out = QAction(self)
        act_zoom_out.setShortcut("Ctrl+-")
        act_zoom_out.triggered.connect(self.zoom_out)
        self.addAction(act_zoom_out)

        act_zoom_reset = QAction(self)
        act_zoom_reset.setShortcut("Ctrl+0")
        act_zoom_reset.triggered.connect(self.reset_zoom)
        self.addAction(act_zoom_reset)

        # (선택) 종료 단축키를 쓰고 싶다면 주석 해제
        # act_quit = QAction(self)
        # act_quit.setShortcut("Ctrl+Q")
        # act_quit.triggered.connect(QApplication.quit)
        # self.addAction(act_quit)

    # ---------------- Downloads ----------------
    def on_download_requested(self, item: QWebEngineDownloadRequest):
        suggested = item.suggestedFileName() or "download"
        path, _ = QFileDialog.getSaveFileName(self, "파일 저장", suggested)
        if path:
            item.setDownloadFileName(os.path.basename(path))
            item.setDownloadDirectory(os.path.dirname(path))
            self.download_manager.add_download(item)
            item.accept()
        else:
            item.cancel()

    # ---------------- Browser Core ----------------
    def _has_plus_tab(self) -> bool:
        return self.tabs.count() > 0 and self.tabs.tabText(self.tabs.count() - 1) == "+"

    def _is_plus_index(self, index: int) -> bool:
        return 0 <= index < self.tabs.count() and self.tabs.tabText(index) == "+"

    def _run_on_current_view(self, action):
        view = self.current_view()
        if view:
            action(view)

    def _ensure_plus_tab(self):
        # 맨 끝이 +가 아니면 추가, 맞으면 닫기 버튼 비활성 느낌으로 유지
        if not self._has_plus_tab():
            idx = self.tabs.addTab(QWidget(), "+")
            # 닫기 버튼/아이콘 제거
            self.tabs.tabBar().setTabButton(idx, QTabBar.RightSide, None)
            self.tabs.tabBar().setTabButton(idx, QTabBar.LeftSide, None)

    def _open_tab_from_plus(self, index: int):
        if not self._is_plus_index(index):
            return
        self.tabs.removeTab(index)
        self.create_new_tab(self.get_home_url())
        self._ensure_plus_tab()

    def _on_tab_changed(self, index: int):
        # + 탭 클릭 시 → 새 탭 만들고 + 유지 (단, 닫는 중엔 무시)
        if self._is_plus_index(index):
            if getattr(self, "_ignore_plus_click", False):
                self.location_bar.clear()
                self._update_star()
                return
            self._open_tab_from_plus(index)
            return
        # 일반 탭이면 URL바 갱신
        self._update_urlbar_from_tab(index)
        self._update_zoom_label()

    def create_new_tab(self, url):
        view = WebView(self.profile, self)
        view.setZoomFactor(self.settings.get("default_zoom", DEFAULT_ZOOM) / 100)
        # 항상 + 탭 바로 앞에 삽입(있다면)
        insert_at = self.tabs.count()
        if self._has_plus_tab():
            insert_at -= 1
        i = self.tabs.insertTab(insert_at, view, "New Tab")
        self.tabs.setCurrentIndex(i)

        def set_tab_title_from_view(v: QWebEngineView, title: str | None = None):
            idx = self.tabs.indexOf(v)
            if idx != -1:
                self.tabs.setTabText(idx, title or v.title() or "New Tab")

        def set_tab_icon_from_view(v: QWebEngineView):
            idx = self.tabs.indexOf(v)
            if idx != -1:
                self.tabs.setTabIcon(idx, v.icon())

        view.titleChanged.connect(lambda _t, v=view: set_tab_title_from_view(v))
        view.iconChanged.connect(lambda _i, v=view: set_tab_icon_from_view(v))
        view.loadStarted.connect(lambda v=view: set_tab_title_from_view(v, "Loading…"))
        view.loadFinished.connect(lambda ok, v=view: (set_tab_title_from_view(v), self._on_view_load_finished(v, ok)))
        view.urlChanged.connect(lambda qurl, v=view: (self._update_urlbar(qurl, v), self._update_star()))
        view.setUrl(QUrl(url))

        # 새 탭 만든 후에도 + 탭은 항상 끝에 유지
        self._ensure_plus_tab()
        self._update_zoom_label()
        return view

    def _actual_tab_views(self):
        result = []
        for idx in range(self.tabs.count()):
            widget = self.tabs.widget(idx)
            if isinstance(widget, QWebEngineView):
                result.append((idx, widget))
        return result

    def _current_actual_index(self):
        current = self.current_view()
        for pos, (_idx, view) in enumerate(self._actual_tab_views()):
            if view == current:
                return pos
        return 0

    def _session_tabs(self):
        tabs = []
        for _idx, view in self._actual_tab_views():
            url = view.url().toString()
            if url:
                tabs.append({"url": url, "title": view.title() or "New Tab"})
        return tabs

    def _save_session(self):
        if self._skip_next_session_save:
            return
        data = {
            "tabs": self._session_tabs(),
            "current_index": self._current_actual_index(),
            "recent_closed": self.recent_closed_tabs[:MAX_RECENT_CLOSED],
            "saved_at": now_iso(),
        }
        save_json_file(SESSION_FILE, data)

    def _restore_session(self):
        if not self.settings.get("restore_session", False):
            return False
        tabs = self.saved_session.get("tabs", [])
        valid_tabs = [tab for tab in tabs if tab.get("url")]
        if not valid_tabs:
            return False
        for tab in valid_tabs:
            self.create_new_tab(tab["url"])
        actuals = self._actual_tab_views()
        if actuals:
            current_index = clamp(self.saved_session.get("current_index", 0), 0, len(actuals) - 1)
            self.tabs.setCurrentIndex(actuals[current_index][0])
        return True

    def _push_recent_closed_tab(self, url, title):
        if not url:
            return
        item = {"url": url, "title": title or url, "closed_at": now_iso()}
        self.recent_closed_tabs = [tab for tab in self.recent_closed_tabs if tab.get("url") != url]
        self.recent_closed_tabs.insert(0, item)
        self.recent_closed_tabs = self.recent_closed_tabs[:MAX_RECENT_CLOSED]

    def restore_recent_closed_tab(self):
        if not self.recent_closed_tabs:
            self.status_label.setText("최근 닫은 탭이 없습니다.")
            return
        item = self.recent_closed_tabs.pop(0)
        url = item.get("url", "")
        if url:
            self.create_new_tab(url)

    def _on_view_load_finished(self, view, ok):
        if ok:
            self._record_history(view.url().toString(), view.title())
        self._update_zoom_label()

    def _record_history(self, url, title):
        if not url or url == "about:blank":
            return
        self.history.insert(0, {
            "url": url,
            "title": title or url,
            "visited_at": now_iso(),
        })
        self._prune_history(save=False)
        self._save_history()
        if self.history_dialog and self.history_dialog.isVisible():
            self.history_dialog.refresh()

    def delete_history_item(self, index):
        if 0 <= index < len(self.history):
            del self.history[index]
            self._save_history()

    def clear_history(self):
        self.history = []
        self._save_history()
        if hasattr(self.profile, "clearAllVisitedLinks"):
            self.profile.clearAllVisitedLinks()
        if self.history_dialog and self.history_dialog.isVisible():
            self.history_dialog.refresh()
        self.status_label.setText("방문 기록을 삭제했습니다.")

    def close_tab(self, index):
        if not (0 <= index < self.tabs.count()):
            return

        # + 탭은 닫지 않음
        if self._is_plus_index(index):
            return

        view = self.tabs.widget(index)
        if not self._closing_app and isinstance(view, QWebEngineView):
            self._push_recent_closed_tab(view.url().toString(), view.title())

        # 닫은 뒤 선택될 대상 인덱스 미리 계산
        # - 기본: 방금 닫은 탭의 왼쪽(index-1)을 우선
        # - 맨 왼쪽 탭을 닫는다면 0
        target = index - 1 if index > 0 else 0

        # 탭 닫는 동안 + 탭 자동 생성 방지
        self._ignore_plus_click = True
        try:
            self.tabs.removeTab(index)
            self._ensure_plus_tab()

            new_count = self.tabs.count()
            if new_count == 0:
                return  # 정말 아무 탭도 없으면 선택 불가 (거의 안 옴)

            # 방금 계산한 target이 범위를 벗어나면 보정
            if target >= new_count:
                target = new_count - 1
            if target < 0:
                target = 0

            # 만약 target이 + 탭이면, 실탭이 남아 있을 경우 마지막 실탭으로 보정
            if self._is_plus_index(target) and new_count > 1:
                target = new_count - 2  # 마지막 실탭

            # 최종 포커스 적용
            self.tabs.setCurrentIndex(target)
            if self._is_plus_index(target):
                self.location_bar.clear()
                self._update_star()
            self._update_zoom_label()

        finally:
            # 이벤트 루프 한 사이클 뒤 플래그 해제 (currentChanged 처리 이후)
            QTimer.singleShot(0, lambda: setattr(self, "_ignore_plus_click", False))


    def current_view(self):
        w = self.tabs.currentWidget()
        return w if isinstance(w, QWebEngineView) else None

    def load_from_location(self):
        text = self.location_bar.text().strip()
        if not text:
            return
        if "://" in text:
            url = text
        elif self._looks_like_url(text):
            url = "http://" + text
        else:
            url = f"https://www.google.com/search?q={quote_plus(text)}"
        v = self.current_view()
        if v:
            v.setUrl(QUrl(url))
        else:
            self.create_new_tab(url)

    def _looks_like_url(self, text: str) -> bool:
        if any(ch.isspace() for ch in text):
            return False
        lowered = text.lower()
        host, sep, port = text.rpartition(":")
        has_port = bool(sep and host and port.isdigit())
        return lowered == "localhost" or lowered.startswith("localhost:") or has_port or "." in text or "/" in text

    def _update_urlbar(self, qurl, view):
        if view == self.current_view():
            self.location_bar.setText(qurl.toString())
            self.location_bar.setCursorPosition(0)
            self._update_star()

    def _update_urlbar_from_tab(self, index):
        view = self.tabs.widget(index)
        if isinstance(view, QWebEngineView):
            self.location_bar.setText(view.url().toString())
            self._update_star()

    # ---------------- Theme / zoom / settings ----------------
    def _system_prefers_dark(self):
        app = QApplication.instance()
        if not app:
            return False
        color = app.palette().color(QPalette.Window)
        return color.lightness() < 128

    def apply_theme(self):
        theme = self.settings.get("theme", "system")
        use_dark = theme == "dark" or (theme == "system" and self._system_prefers_dark())
        app = QApplication.instance()
        if app:
            app.setStyleSheet(DARK_STYLE if use_dark else LIGHT_STYLE)

    def _current_zoom_percent(self):
        view = self.current_view()
        if view:
            return int(round(view.zoomFactor() * 100))
        return int(self.settings.get("default_zoom", DEFAULT_ZOOM))

    def _update_zoom_label(self):
        if hasattr(self, "zoom_status_action"):
            self.zoom_status_action.setText(f"확대율: {self._current_zoom_percent()}%")

    def set_current_zoom(self, percent):
        view = self.current_view()
        if not view:
            return
        percent = clamp(int(percent), MIN_ZOOM, MAX_ZOOM)
        view.setZoomFactor(percent / 100)
        self._update_zoom_label()

    def zoom_in(self):
        self.set_current_zoom(self._current_zoom_percent() + ZOOM_STEP)

    def zoom_out(self):
        self.set_current_zoom(self._current_zoom_percent() - ZOOM_STEP)

    def reset_zoom(self):
        self.set_current_zoom(self.settings.get("default_zoom", DEFAULT_ZOOM))

    def show_history(self):
        self.history_dialog = HistoryDialog(self, self)
        self.history_dialog.show()

    def show_settings(self):
        dialog = SettingsDialog(self, self)
        if dialog.exec() == QDialog.Accepted:
            self.apply_settings(dialog.values())

    def apply_settings(self, values):
        self.settings.update(values)
        self.settings["home_url"] = self._normalize_home_url(self.settings.get("home_url", HOME_URL))
        self.settings["default_zoom"] = clamp(int(self.settings["default_zoom"]), MIN_ZOOM, MAX_ZOOM)
        self.settings["history_retention_days"] = max(1, int(self.settings["history_retention_days"]))
        self._save_settings()
        self._refresh_bookmarks_toolbar()
        self.apply_theme()
        self._prune_history(save=True)
        self.reset_zoom()

    def clear_cache(self):
        self.profile.clearHttpCache()
        self._cleanup_shared_dictionary_store(self.storage_path)
        self.status_label.setText("캐시 삭제를 요청했습니다.")
        QMessageBox.information(self, "캐시 삭제", "캐시 삭제를 요청했습니다.")

    def clear_cookies(self):
        self.profile.cookieStore().deleteAllCookies()
        self.status_label.setText("쿠키를 삭제했습니다.")
        QMessageBox.information(self, "쿠키 삭제", "쿠키를 삭제했습니다.")

    def clear_saved_session(self):
        self.recent_closed_tabs = []
        self._skip_next_session_save = True
        try:
            if os.path.exists(SESSION_FILE):
                os.remove(SESSION_FILE)
        except Exception as exc:
            QMessageBox.warning(self, "세션 삭제", f"세션 파일을 삭제하지 못했습니다.\n{exc}")
            return
        self.status_label.setText("저장된 세션을 삭제했습니다.")
        QMessageBox.information(self, "세션 삭제", "저장된 세션을 삭제했습니다.")

    # ---------------- 검색 ----------------
    def _build_find_flags(self, backward: bool = False) -> QWebEnginePage.FindFlags:
        flags = QWebEnginePage.FindFlags()
        if self.chk_case.isChecked():
            flags |= QWebEnginePage.FindCaseSensitively
        if backward:
            flags |= QWebEnginePage.FindBackward
        return flags

    def show_find_bar(self):
        self.find_tb.show()
        self.find_bar.show()
        self.find_bar.setFocus()
        self.find_bar.selectAll()

    def _find_from_enter(self):
        modifiers = QApplication.keyboardModifiers()
        if modifiers & Qt.ShiftModifier:
            self._find_prev()
        else:
            self._find_next()

    def _find_next(self):
        text = self.find_bar.text().strip()
        if not text:
            return
        view = self.current_view()
        if view:
            view.findText("", QWebEnginePage.FindFlags())
            view.findText(text, self._build_find_flags(backward=False))

    def _find_prev(self):
        text = self.find_bar.text().strip()
        if not text:
            return
        view = self.current_view()
        if view:
            view.findText("", QWebEnginePage.FindFlags())
            view.findText(text, self._build_find_flags(backward=True))

    def _close_find(self):
        view = self.current_view()
        if view:
            view.findText("")  # 하이라이트 초기화
        self.find_bar.clear()
        self.find_tb.hide()

    def eventFilter(self, source, event):
        if source == self.find_bar and event.type() == QEvent.KeyPress and event.key() == Qt.Key_Escape:
            self._close_find()
            return True
        return super().eventFilter(source, event)

    # ---------------- 즐겨찾기: 추가/토글 ----------------
    def add_bookmark(self):
        view = self.current_view()
        if not view:
            return
        default_title = view.title() or "무제"
        url = view.url().toString()

        if self._is_bookmarked(url):
            QMessageBox.information(self, "즐겨찾기", "이미 즐겨찾기에 등록된 페이지입니다.")
            self._update_star()
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("즐겨찾기 추가")
        form = QFormLayout(dialog)

        title_edit = QLineEdit(default_title)
        url_label = QLabel(url)
        url_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        form.addRow("제목:", title_edit)
        form.addRow("URL:", url_label)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        form.addWidget(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        if dialog.exec() == QDialog.Accepted:
            title = title_edit.text().strip() or default_title
            self.bookmarks.append({"title": title, "url": url})
            self._save_bookmarks()
            self.bookmark_manager.refresh()
            self._update_star()
            QMessageBox.information(self, "즐겨찾기", f"'{title}' 이(가) 즐겨찾기에 추가되었습니다.")

    def toggle_bookmark_current(self):
        view = self.current_view()
        if not view:
            return
        url = view.url().toString()
        if self._is_bookmarked(url):
            self._remove_bookmark_by_url(url)
            QMessageBox.information(self, "즐겨찾기", "현재 페이지가 즐겨찾기에서 제거되었습니다.")
            self._update_star()
        else:
            self.add_bookmark()

    # ---------------- 단축키 일러두기 ----------------
    def show_shortcuts(self):
        ShortcutsDialog(self).exec()

    def closeEvent(self, event):
        self._closing_app = True
        self._save_session()
        super().closeEvent(event)

# ------------------------------------------------------
# 🚀 메인
# ------------------------------------------------------
def main():
    configure_chromium_flags()
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(resource_path("kyobrowser.ico")))
    browser = Browser()
    browser.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
