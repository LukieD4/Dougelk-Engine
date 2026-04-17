import ctypes
import threading
import time

user32 = ctypes.windll.user32

WM_CLOSE = 0x0010

class LoadingDialog:
    def __init__(self, title="Game", text="Loading..."):
        self.title = title
        self.text = text
        self.hwnd = None
        self.thread = None

    def show(self):
        def worker():
            # Show dialog (blocking)
            user32.MessageBoxW(0, self.text, self.title, 0)

        def find_window():
            # Wait until window exists
            while self.hwnd is None:
                hwnd = user32.FindWindowW(None, self.title)
                if hwnd:
                    self.hwnd = hwnd
                    break
                time.sleep(0.01)

        self.thread = threading.Thread(target=worker, daemon=True)
        self.thread.start()

        # Capture HWND
        find_window()

    def close(self):
        if self.hwnd:
            user32.PostMessageW(self.hwnd, WM_CLOSE, 0, 0)


dlg = LoadingDialog("Game", "Loading game...")