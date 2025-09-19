import sys
import os
import json
import shutil
from PySide6.QtCore import QUrl, QSize, Qt, Signal, QEvent
from PySide6.QtGui import QAction, QDesktopServices, QKeySequence, QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QLineEdit, QToolBar, QFileDialog,
    QLabel, QTabWidget, QDialog, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget, QHBoxLayout, QPushButton,
    QMenu, QToolButton, QMessageBox, QTabBar, QCheckBox,
    QFormLayout, QDialogButtonBox
)
from PySide6.QtWebEngineCore import (
    QWebEngineProfile, QWebEnginePage, QWebEngineDownloadRequest, QWebEngineUrlRequestInterceptor
)
from PySide6.QtWebEngineWidgets import QWebEngineView

if os.name == "nt":
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Kyo.Browser")

HOME_URL = "https://www.google.com"

def get_user_data_dir() -> str:
    """사용자 프로필 하위에 KyoBrowser 데이터 폴더를 만든다."""
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or os.path.expanduser("~")
    path = os.path.join(base, "KyoBrowser")
    os.makedirs(path, exist_ok=True)
    return path

# 전역 경로 상수
USER_DATA_DIR = get_user_data_dir()
BOOKMARK_FILE = os.path.join(USER_DATA_DIR, "bookmarks.json")

# (선택) 구버전 위치에 있던 즐겨찾기 자동 마이그레이션
try:
    legacy_bm = os.path.join(os.getcwd(), "bookmarks.json")
    if os.path.exists(legacy_bm) and not os.path.exists(BOOKMARK_FILE):
        shutil.copy2(legacy_bm, BOOKMARK_FILE)
except Exception:
    pass

def resource_path(name: str) -> str:
    """PyInstaller --onefile 또는 직접 실행 모두 대응"""
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, name)


class CloseOnMiddleClickTabBar(QTabBar):
    middleClickClose = Signal(int)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MiddleButton:
            idx = self.tabAt(e.pos())
            if idx != -1:
                self.middleClickClose.emit(idx)
        super().mouseReleaseEvent(e)


# -------------------- Request Interceptor --------------------
class MyInterceptor(QWebEngineUrlRequestInterceptor):
    def interceptRequest(self, info):
        info.setHttpHeader(b"Accept-Language", b"ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7")


# -------------------- Download Manager (간단 창) --------------------
class DownloadManager(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("다운로드 관리자")
        self.resize(600, 300)

        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 5, self)
        self.table.setHorizontalHeaderLabels(["파일명", "크기", "진행률", "상태", "액션"])
        layout.addWidget(self.table)


# -------------------- Bookmark Manager (별도 창) --------------------
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

            btn_open.clicked.connect(lambda checked=False, url=bm["url"]: self.browser.create_new_tab(url))
            btn_edit.clicked.connect(lambda checked=False, i=idx: self.edit_bookmark(i))
            btn_delete.clicked.connect(lambda checked=False, i=idx: self.delete_bookmark(i))

    def delete_bookmark(self, index: int):
        if 0 <= index < len(self.browser.bookmarks):
            del self.browser.bookmarks[index]
            self.browser._save_bookmarks()
            self.refresh()
            self.browser._update_star()

    def edit_bookmark(self, index: int):
        if not (0 <= index < len(self.browser.bookmarks)):
            return

        bm = self.browser.bookmarks[index]
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
                bm["url"] = new_url
                self.browser._save_bookmarks()
                self.refresh()
                self.browser._update_star()


# -------------------- WebView --------------------
class WebView(QWebEngineView):
    def __init__(self, profile, browser, parent=None):
        super().__init__(parent)
        self.browser = browser
        self.setPage(QWebEnginePage(profile, self))
        self.page().profile().downloadRequested.connect(self.on_download_requested)

    def on_download_requested(self, item: QWebEngineDownloadRequest):
        suggested = item.suggestedFileName() or "download"
        path, _ = QFileDialog.getSaveFileName(self, "파일 저장", suggested)
        if path:
            item.setDownloadFileName(os.path.basename(path))
            item.setDownloadDirectory(os.path.dirname(path))
            item.accept()
            self.browser.download_manager.show()
        else:
            item.cancel()

    def createWindow(self, _type):
        return self.browser.create_new_tab(HOME_URL)


# -------------------- About Dialog --------------------
class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About Kyo Browser")
        self.resize(400, 250)

        layout = QVBoxLayout(self)
        label = QLabel(
            """
            <h2>Kyo Browser 1.0</h2>
            <p>답답함을 해결하기 위해 직접 만든 브라우저</p>
            <p><b>E-mail:</b> dersertfox@kakao.com</p>
            <hr>
            <p>Developed by <b>Kyo</b></p>
            <p>Powered by <b>PySide6 / QtWebEngine</b></p>
            <p style="font-size:10px; color:gray;">
                © 2025 Kyo. All rights reserved.
            </p>
            """
        )
        label.setAlignment(Qt.AlignCenter)
        label.setWordWrap(True)
        layout.addWidget(label)

        btn = QPushButton("닫기")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn, alignment=Qt.AlignCenter)


# -------------------- Shortcuts Dialog --------------------
class ShortcutsDialog(QDialog):
    """단축키 일러두기 다이얼로그"""
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
            ("찾기: 다음 결과", "Enter (검색창 포커스 중)"),
            ("찾기: 이전 결과", "Shift + Enter (검색창 포커스 중)"),
            ("찾기 닫기", "Esc (검색창 포커스 중)"),
            ("탭 닫기", "마우스 가운데 버튼(휠)로 탭 클릭"),
        ]

        table.setRowCount(len(data))
        for r, (action, keys) in enumerate(data):
            table.setItem(r, 0, QTableWidgetItem(action))
            table.setItem(r, 1, QTableWidgetItem(keys))

        table.resizeColumnsToContents()
        layout.addWidget(table)

        btns = QDialogButtonBox(QDialogButtonBox.Close)
        btns.rejected.connect(self.reject)
        btns.accepted.connect(self.accept)
        # Close 버튼만 있으므로 close에 연결
        for b in btns.buttons():
            b.clicked.connect(self.accept)
        layout.addWidget(btns)


# -------------------- Browser --------------------
class Browser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kyo's Browser")
        self.resize(1200, 800)

        # 아이콘 로드
        icon = None
        try:
            icon_path = resource_path("kyobrowser.ico")
            if os.path.exists(icon_path):
                icon = QIcon(icon_path)
            elif os.path.exists("kyobrowser.ico"):
                icon = QIcon("kyobrowser.ico")
        except Exception:
            pass
        if icon is None or icon.isNull():
            icon = QIcon()
        self.setWindowIcon(icon)

        # 프로필
        storage_path = os.path.join(USER_DATA_DIR, "browser_data")
        os.makedirs(storage_path, exist_ok=True)

        self.profile = QWebEngineProfile("KyoProfile")
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.ForcePersistentCookies)
        self.profile.setCachePath(os.path.join(storage_path, "cache"))
        self.profile.setPersistentStoragePath(os.path.join(storage_path, "storage"))
        self.profile.setHttpUserAgent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        )
        self.profile.setUrlRequestInterceptor(MyInterceptor())

        # 탭
        self.tabs = QTabWidget()
        midclose_tabbar = CloseOnMiddleClickTabBar(self.tabs)
        midclose_tabbar.middleClickClose.connect(self.close_tab)
        self.tabs.setTabBar(midclose_tabbar)
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.setDocumentMode(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self._update_urlbar_from_tab)
        self.setCentralWidget(self.tabs)

        # 주소창
        self.location_bar = QLineEdit(self)
        self.location_bar.setClearButtonEnabled(True)
        self.location_bar.returnPressed.connect(self.load_from_location)

        # 상태바
        self.status_label = QLabel("")
        self.statusBar().addPermanentWidget(self.status_label)

        # 데이터
        self.bookmarks = self._load_bookmarks()
        self.download_manager = DownloadManager(self)
        self.bookmark_manager = BookmarkManager(self, self)

        # 툴바/단축키/초기 탭
        self._build_toolbar()
        self.create_new_tab(HOME_URL)
        self._setup_shortcuts()
        self._update_star()

        # 🔍 검색 툴바 (라인에딧 + 옵션 + 이전/다음/닫기 버튼)
        self.find_bar = QLineEdit(self)
        self.find_bar.setPlaceholderText("검색어 입력 후 Enter…")
        self.find_bar.returnPressed.connect(self._find_from_enter)
        self.find_bar.installEventFilter(self)  # ESC 감지용

        self.chk_case = QCheckBox("Aa", self)
        self.chk_case.setToolTip("대소문자 구분")

        self.chk_whole = QCheckBox("W", self)
        self.chk_whole.setToolTip("단어 전체 일치")

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
        find_tb.addWidget(self.chk_whole)
        find_tb.addWidget(self.btn_prev)
        find_tb.addWidget(self.btn_next)
        find_tb.addWidget(self.btn_close_find)
        self.addToolBar(Qt.BottomToolBarArea, find_tb)
        self.find_tb = find_tb
        self.find_tb.hide()

    # ---------------- Bookmark helpers ----------------
    def _load_bookmarks(self):
        if os.path.exists(BOOKMARK_FILE):
            try:
                with open(BOOKMARK_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data if isinstance(data, list) else []
            except Exception:
                return []
        return []

    def _save_bookmarks(self):
        with open(BOOKMARK_FILE, "w", encoding="utf-8") as f:
            json.dump(self.bookmarks, f, ensure_ascii=False, indent=2)

    def _is_bookmarked(self, url: str) -> bool:
        return any(bm.get("url") == url for bm in self.bookmarks)

    def _remove_bookmark_by_url(self, url: str):
        before = len(self.bookmarks)
        self.bookmarks = [bm for bm in self.bookmarks if bm.get("url") != url]
        if len(self.bookmarks) != before:
            self._save_bookmarks()
            self.bookmark_manager.refresh()

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

    # ---------------- 즐겨찾기: 추가(제목 편집 다이얼로그 포함) ----------------
    def add_bookmark(self):
        view = self.current_view()
        if not view:
            return
        default_title = view.title() or "무제"
        url = view.url().toString()

        # 이미 등록된 URL이면 안내 후 종료
        if self._is_bookmarked(url):
            QMessageBox.information(self, "즐겨찾기", "이미 즐겨찾기에 등록된 페이지입니다.")
            self._update_star()
            return

        # 제목 편집 다이얼로그
        dialog = QDialog(self)
        dialog.setWindowTitle("즐겨찾기 추가")
        form = QFormLayout(dialog)

        title_edit = QLineEdit(default_title)
        url_label = QLabel(url)  # URL은 읽기 전용(표시만)
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

    # ---------------- Toolbar ----------------
    def _build_toolbar(self):
        tb = QToolBar("Navigation", self)
        tb.setIconSize(QSize(18, 18))
        self.addToolBar(tb)

        back_action = QAction("◀", self)
        back_action.triggered.connect(lambda: self.current_view().back())
        tb.addAction(back_action)

        fwd_action = QAction("▶", self)
        fwd_action.triggered.connect(lambda: self.current_view().forward())
        tb.addAction(fwd_action)

        reload_action = QAction("🔄", self)
        reload_action.triggered.connect(lambda: self.current_view().reload())
        tb.addAction(reload_action)

        home_action = QAction("🏠", self)
        home_action.triggered.connect(lambda: self.current_view().setUrl(QUrl(HOME_URL)))
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

        act_downloads = QAction("다운로드 관리자", self)
        act_downloads.triggered.connect(lambda: self.download_manager.show())
        menu.addAction(act_downloads)

        act_bookmarks = QAction("즐겨찾기 관리자", self)
        act_bookmarks.triggered.connect(lambda: self.bookmark_manager.show())
        menu.addAction(act_bookmarks)

        # ➕ 단축키 일러두기
        act_shortcuts = QAction("단축키 일러두기", self)
        act_shortcuts.triggered.connect(self.show_shortcuts)
        menu.addAction(act_shortcuts)

        act_about = QAction("About", self)
        act_about.triggered.connect(lambda: AboutDialog(self).exec())
        menu.addAction(act_about)

        menu_button.setMenu(menu)
        tb.addWidget(menu_button)

    # ---------------- Shortcuts ----------------
    def _setup_shortcuts(self):
        act_focus_url = QAction(self)
        act_focus_url.setShortcut(QKeySequence("Ctrl+L"))
        act_focus_url.triggered.connect(lambda: (self.location_bar.setFocus(), self.location_bar.selectAll()))
        self.addAction(act_focus_url)

        act_new_tab = QAction(self)
        act_new_tab.setShortcut(QKeySequence("Ctrl+T"))
        act_new_tab.triggered.connect(lambda: self.create_new_tab(HOME_URL))
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

    # ---------------- Browser Core ----------------
    def create_new_tab(self, url):
        view = WebView(self.profile, self)
        i = self.tabs.addTab(view, "New Tab")
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
        view.loadFinished.connect(lambda ok, v=view: set_tab_title_from_view(v))
        view.urlChanged.connect(lambda qurl, v=view: (self._update_urlbar(qurl, v), self._update_star()))
        view.setUrl(QUrl(url))
        return view

    def close_tab(self, index):
        if self.tabs.count() > 1:
            self.tabs.removeTab(index)

    def current_view(self):
        return self.tabs.currentWidget()

    def load_from_location(self):
        text = self.location_bar.text().strip()
        if text.startswith("http://") or text.startswith("https://"):
            url = text
        elif "." in text:
            url = "http://" + text
        else:
            url = f"https://www.google.com/search?q={text}"
        self.current_view().setUrl(QUrl(url))

    def _update_urlbar(self, qurl, view):
        if view == self.current_view():
            self.location_bar.setText(qurl.toString())
            self.location_bar.setCursorPosition(0)
            self._update_star()

    def _update_urlbar_from_tab(self, index):
        view = self.tabs.widget(index)
        if view:
            self.location_bar.setText(view.url().toString())
            self._update_star()

    # ---------------- 검색 ----------------
    def _build_find_flags(self, backward: bool = False) -> QWebEnginePage.FindFlags:
        flags = QWebEnginePage.FindFlags()
        if self.chk_case.isChecked():
            flags |= QWebEnginePage.FindCaseSensitively
        if self.chk_whole.isChecked():
            flags |= QWebEnginePage.FindWholeWords
        if backward:
            flags |= QWebEnginePage.FindBackward
        return flags

    def show_find_bar(self):
        self.find_tb.show()
        self.find_bar.show()
        self.find_bar.setFocus()
        self.find_bar.selectAll()

    def _find_from_enter(self):
        """Enter/Shift+Enter 처리"""
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
            view.findText("", QWebEnginePage.FindFlags())  # 하이라이트 초기화
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
        """검색창 닫기 + 하이라이트 해제"""
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

    # ---------------- 즐겨찾기: ☆/★ 토글 버튼 ----------------
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


def main():
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(resource_path("kyobrowser.ico")))
    browser = Browser()
    browser.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
