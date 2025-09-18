import sys
from cefpython3 import cefpython as cef


def main():
    sys.excepthook = cef.ExceptHook  # 예외 처리
    settings = {
        "cache_path": "cef_cache",   # 쿠키/세션/캐시 유지
    }
    cef.Initialize(settings=settings)

    # 새 브라우저 윈도우 열기
    browser = cef.CreateBrowserSync(
        url="https://www.google.com",
        window_title="Kyo's CEF Browser"
    )

    cef.MessageLoop()
    cef.Shutdown()


if __name__ == "__main__":
    main()
