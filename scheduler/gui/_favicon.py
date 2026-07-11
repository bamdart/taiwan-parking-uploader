"""
gui/_favicon.py - 內嵌 ICO 圖示（base64）

將 favicon.ico 以 base64 直接編入程式碼，避免 PyInstaller onefile 模式
因外部資源檔路徑問題或防毒軟體干擾而找不到圖示。

原始檔：scheduler/resources/favicon.ico
"""

import base64

# favicon.ico 的 base64 編碼
_FAVICON_B64 = (
    "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"
    "AAAASUVORK5CYII="
)


def favicon_bytes() -> bytes:
    """回傳 favicon.ico 的二進位資料。"""
    return base64.b64decode(_FAVICON_B64)


def favicon_qicon():
    """建立並回傳 QIcon（從內嵌 base64 ico 資料）。"""
    from PySide6.QtCore import QByteArray
    from PySide6.QtGui import QIcon, QPixmap

    pixmap = QPixmap()
    pixmap.loadFromData(QByteArray(favicon_bytes()), "ICO")
    return QIcon(pixmap)
