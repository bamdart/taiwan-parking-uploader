"""
gui/brand.py - HITech 品牌設計規範 QSS

依據 HITech 海姆達爾品牌設計規範，定義全域 QSS 樣式。
支援明亮/黑暗兩種主題與三種字級。

色彩（品牌固定）：
  Primary 1 深藍 #0041C0 — 標題、強調區塊
  Primary 2 亮藍 #017CFD — 按鈕、連結
  Secondary 青色 #30E0FF — 裝飾、成功色
  Green #17A48A — 成功
  Red #A2230A — 錯誤
  Yellow #FACC00 — 警告

主題：
  light / dark，由 config.theme 決定（system 會自動解析）
"""

# ------------------------------------------------------------------
# 品牌色彩常數（不隨主題變化）
# ------------------------------------------------------------------

PRIMARY_1 = "#0041C0"  # 深藍
PRIMARY_2 = "#017CFD"  # 亮藍
SECONDARY = "#30E0FF"  # 青色
WARNING = "#FACC00"    # 黃色
ERROR = "#A2230A"      # 紅色
SUCCESS = "#17A48A"    # 綠色

# ------------------------------------------------------------------
# 主題色盤
# ------------------------------------------------------------------

LIGHT_THEME = {
    "bg": "#FFFFFF",          # 視窗背景
    "surface": "#FFFFFF",     # 卡片、輸入欄背景
    "surface_alt": "#F5F5F5", # 次要表面（disabled bg）
    "border": "#DDDEDF",      # 邊框
    "divider": "#DDDEDF",     # 分隔線
    "text": "#000000",        # 主要文字
    "text_muted": "#8C939C",  # 次要文字
    "text_disabled": "#B3B7BD",
    "menu_bg": "#FFFFFF",
    "log_bg": "#FFFFFF",
    "shadow": "rgba(0,0,0,0.15)",
}

DARK_THEME = {
    "bg": "#1E1E1E",
    "surface": "#2D2D2D",
    "surface_alt": "#3A3A3A",
    "border": "#404040",
    "divider": "#404040",
    "text": "#FFFFFF",
    "text_muted": "#B3B7BD",
    "text_disabled": "#6A6A6A",
    "menu_bg": "#2D2D2D",
    "log_bg": "#252525",
    "shadow": "rgba(0,0,0,0.5)",
}

# 便利別名（取決於目前主題，初始化為 light）
BG = LIGHT_THEME["bg"]
SURFACE = LIGHT_THEME["surface"]
BORDER = LIGHT_THEME["border"]
TEXT = LIGHT_THEME["text"]
TEXT_MUTED = LIGHT_THEME["text_muted"]
BLACK = "#000000"  # 保留舊名，但實際使用建議換成 TEXT
WHITE = "#FFFFFF"
GREY_LIGHT = "#DDDEDF"
GREY_MIDDLE = "#B3B7BD"
GREY_DARK = "#8C939C"

_current_theme_key = "light"
_current_theme = LIGHT_THEME


# ------------------------------------------------------------------
# 字體
# ------------------------------------------------------------------

FONT_FAMILY = (
    "'Noto Sans TC', 'Microsoft JhengHei', 'Montserrat', 'Calibri', sans-serif"
)

FONT_SIZE_PRESETS = {
    "standard": {
        "label": "標準",
        "base": 13, "small": 11, "tiny": 9, "button": 13, "input": 13,
        "menu": 13, "log": 12, "title": 18, "group": 13, "icon": 18, "company": 11,
    },
    "large": {
        "label": "大",
        "base": 15, "small": 13, "tiny": 11, "button": 15, "input": 15,
        "menu": 15, "log": 14, "title": 21, "group": 15, "icon": 22, "company": 13,
    },
    "xlarge": {
        "label": "特大",
        "base": 18, "small": 15, "tiny": 13, "button": 17, "input": 17,
        "menu": 17, "log": 16, "title": 24, "group": 17, "icon": 26, "company": 15,
    },
}

_current_sizes: dict = FONT_SIZE_PRESETS["standard"]


def get_font_sizes() -> dict:
    """取得目前使用的字級 dict。"""
    return _current_sizes


def get_theme() -> dict:
    """取得目前使用的主題色盤 dict。"""
    return _current_theme


def get_theme_key() -> str:
    """取得目前主題的 key（light / dark）。"""
    return _current_theme_key


def is_dark() -> bool:
    """目前是否為黑暗主題。"""
    return _current_theme_key == "dark"


# ------------------------------------------------------------------
# 系統主題偵測
# ------------------------------------------------------------------


def detect_system_theme(app) -> str:
    """偵測系統主題，回傳 'light' 或 'dark'。"""
    try:
        scheme = app.styleHints().colorScheme()
        # Qt.ColorScheme.Dark = 2, Light = 1, Unknown = 0
        if int(scheme) == 2:
            return "dark"
        return "light"
    except (AttributeError, TypeError):
        # Qt 版本不支援時退回讀 palette
        try:
            palette = app.palette()
            bg = palette.window().color()
            # 亮度 < 128 視為深色
            brightness = (bg.red() * 299 + bg.green() * 587 + bg.blue() * 114) / 1000
            return "dark" if brightness < 128 else "light"
        except (AttributeError, TypeError):
            return "light"


def resolve_theme(app, theme_pref: str) -> str:
    """依偏好設定解析實際主題。

    theme_pref: 'system' / 'light' / 'dark'
    """
    if theme_pref == "light" or theme_pref == "dark":
        return theme_pref
    return detect_system_theme(app)


# ------------------------------------------------------------------
# QSS 產生函式
# ------------------------------------------------------------------


def _build_app_qss(s: dict, t: dict) -> str:
    """根據字級與主題色盤產生全域 QSS。"""
    # 標題色：淺色模式用深藍，深色模式用白（增強對比）
    title_color = WHITE if t is DARK_THEME else PRIMARY_1
    return f"""
/* ===== 全域 ===== */
* {{
    font-family: {FONT_FAMILY};
    font-size: {s['base']}px;
}}

QMainWindow, QWidget {{
    background: {t['bg']};
    color: {t['text']};
}}

/* ===== 選單列 ===== */
QMenuBar {{
    background: {t['menu_bg']};
    color: {t['text']};
    border-bottom: 2px solid {PRIMARY_1};
    padding: 2px 0;
    font-size: {s['menu']}px;
}}
QMenuBar::item {{
    padding: 4px 12px;
    border-radius: 4px;
    color: {t['text']};
    background: transparent;
}}
QMenuBar::item:selected {{
    background: {PRIMARY_2};
    color: {WHITE};
}}
QMenu {{
    background: {t['menu_bg']};
    color: {t['text']};
    border: 1px solid {t['border']};
    padding: 4px 0;
}}
QMenu::item {{
    padding: 6px 24px;
    color: {t['text']};
    font-size: {s['menu']}px;
}}
QMenu::item:selected {{
    background: {PRIMARY_2};
    color: {WHITE};
}}
QMenu::separator {{
    height: 1px;
    background: {t['divider']};
    margin: 4px 8px;
}}

/* ===== Label ===== */
QLabel {{
    color: {t['text']};
    font-size: {s['base']}px;
    background: transparent;
}}

/* 表單欄位 label（粗體） */
QLabel#formLabel {{
    color: {t['text']};
    font-size: {s['base']}px;
    font-weight: 500;
    background: transparent;
}}

/* 單位文字 / 次要說明 */
QLabel#mutedLabel {{
    color: {t['text_muted']};
    font-size: {s['small']}px;
    background: transparent;
}}

/* 狀態訊息（上次/下次/結果） */
QLabel#statusLabel {{
    color: {t['text_muted']};
    font-size: {s['small']}px;
    background: transparent;
}}
QLabel#statusLabelSuccess {{
    color: {SUCCESS};
    font-size: {s['small']}px;
    background: transparent;
}}
QLabel#statusLabelError {{
    color: {ERROR};
    font-size: {s['small']}px;
    background: transparent;
}}

/* 公司名稱 */
QLabel#companyLabel {{
    color: {t['text_muted']};
    font-size: {s['company']}px;
    font-weight: bold;
    background: transparent;
}}

/* Log 標題（淺色模式用深藍，深色模式用白） */
QLabel#logTitle {{
    color: {title_color};
    font-size: {s['base']}px;
    font-weight: bold;
    background: transparent;
}}

/* Wizard / Dialog 標題（淺色模式用深藍，深色模式用白） */
QLabel#wizardTitle {{
    color: {title_color};
    font-size: {s['title']}px;
    font-weight: bold;
    background: transparent;
}}

/* Wizard / Dialog 副標題 */
QLabel#wizardSubtitle {{
    color: {t['text_muted']};
    font-size: {s['small']}px;
    background: transparent;
}}

/* ===== GroupBox ===== */
QGroupBox {{
    font-weight: bold;
    font-size: {s['group']}px;
    color: {t['text']};
    background: {t['surface']};
    border: 1px solid {t['border']};
    border-left: 3px solid {PRIMARY_1};
    border-radius: 6px;
    margin-top: 14px;
    padding: 16px 12px 8px 12px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
    color: {title_color};
}}

/* ===== 按鈕 ===== */
QPushButton {{
    padding: 6px 16px;
    border-radius: 6px;
    font-size: {s['button']}px;
    font-weight: bold;
}}

/* ===== SpinBox ===== */
QSpinBox {{
    padding: 4px 8px;
    border: 1px solid {t['border']};
    border-radius: 4px;
    font-size: {s['input']}px;
    background: {t['surface']};
    color: {t['text']};
    selection-background-color: {PRIMARY_2};
    selection-color: {WHITE};
}}
QSpinBox:focus {{
    border-color: {PRIMARY_2};
}}
QSpinBox::up-button, QSpinBox::down-button {{
    width: 0;
    height: 0;
    border: none;
}}

/* ===== LineEdit ===== */
QLineEdit {{
    padding: 6px 10px;
    border: 1px solid {t['border']};
    border-radius: 6px;
    font-size: {s['input']}px;
    background: {t['surface']};
    color: {t['text']};
    selection-background-color: {PRIMARY_2};
    selection-color: {WHITE};
}}
QLineEdit:focus {{
    border-color: {PRIMARY_2};
}}

/* ===== CheckBox ===== */
QCheckBox {{
    font-size: {s['base']}px;
    spacing: 6px;
    color: {t['text']};
    background: transparent;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 2px solid {t['text_muted']};
    border-radius: 3px;
    background: {t['surface']};
}}
QCheckBox::indicator:checked {{
    background: {PRIMARY_2};
    border-color: {PRIMARY_2};
}}

/* ===== RadioButton ===== */
QRadioButton {{
    font-size: {s['base']}px;
    spacing: 8px;
    color: {t['text']};
    background: transparent;
}}
QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 2px solid {t['text_muted']};
    border-radius: 9px;
    background: {t['surface']};
}}
QRadioButton::indicator:checked {{
    background: {PRIMARY_2};
    border-color: {PRIMARY_2};
}}

/* ===== ScrollBar ===== */
QScrollBar:vertical {{
    width: 8px;
    background: transparent;
}}
QScrollBar::handle:vertical {{
    background: {t['text_muted']};
    border-radius: 4px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background: {t['text']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

/* ===== StatusBar ===== */
QStatusBar {{
    background: {t['bg']};
    border-top: 1px solid {t['divider']};
    font-size: {s['small']}px;
    color: {t['text_muted']};
}}
QStatusBar::item {{
    border: none;  /* 移除元件間的白色分隔線 */
}}

/* ===== ToolTip ===== */
QToolTip {{
    background: {PRIMARY_1};
    color: {WHITE};
    border: none;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: {s['small']}px;
}}

/* ===== TextEdit（Log viewer） ===== */
QTextEdit {{
    border: 1px solid {t['border']};
    border-radius: 6px;
    padding: 4px;
    font-size: {s['log']}px;
    background: {t['log_bg']};
    color: {t['text']};
    selection-background-color: {PRIMARY_2};
    selection-color: {WHITE};
}}

/* ===== MessageBox ===== */
QMessageBox {{
    background: {t['bg']};
}}
QMessageBox QLabel {{
    color: {t['text']};
    font-size: {s['base']}px;
}}
QMessageBox QPushButton {{
    padding: 6px 20px;
    border-radius: 6px;
    font-size: {s['base']}px;
    font-weight: bold;
    border: 1px solid {PRIMARY_2};
    background: {t['surface']};
    color: {PRIMARY_2};
    min-width: 80px;
}}
QMessageBox QPushButton:hover {{
    background: {PRIMARY_2};
    color: {WHITE};
}}
QMessageBox QPushButton:default {{
    background: {PRIMARY_2};
    color: {WHITE};
    border: none;
}}
QMessageBox QPushButton:default:hover {{
    background: {PRIMARY_1};
}}

/* ===== Dialog ===== */
QDialog {{
    background: {t['bg']};
    color: {t['text']};
}}
"""


def _build_btn_qss(s: dict, t: dict) -> dict[str, str]:
    """根據字級與主題產生各按鈕樣式。"""
    primary = f"""
QPushButton {{
    border: none;
    background: {PRIMARY_2};
    color: {WHITE};
    padding: 6px 16px;
    border-radius: 6px;
    font-size: {s['button']}px;
    font-weight: bold;
}}
QPushButton:hover {{
    background: {PRIMARY_1};
}}
QPushButton:pressed {{
    background: #003399;
}}
QPushButton:disabled {{
    background: {t['text_disabled']};
}}
"""

    secondary = f"""
QPushButton {{
    border: 1px solid {PRIMARY_2};
    background: {t['surface']};
    color: {PRIMARY_2};
    padding: 6px 16px;
    border-radius: 6px;
    font-size: {s['button']}px;
    font-weight: bold;
}}
QPushButton:hover {{
    background: {PRIMARY_2};
    color: {WHITE};
}}
QPushButton:pressed {{
    background: {PRIMARY_1};
    border-color: {PRIMARY_1};
    color: {WHITE};
}}
QPushButton:disabled {{
    color: {t['text_disabled']};
    border-color: {t['border']};
    background: {t['surface_alt']};
}}
"""

    danger = f"""
QPushButton {{
    border: 1px solid {ERROR};
    background: {t['surface']};
    color: {ERROR};
    padding: 6px 16px;
    border-radius: 6px;
    font-size: {s['button']}px;
    font-weight: bold;
}}
QPushButton:hover {{
    background: {ERROR};
    color: {WHITE};
}}
QPushButton:pressed {{
    background: #7A1A08;
    border-color: #7A1A08;
    color: {WHITE};
}}
"""
    return {"primary": primary, "secondary": secondary, "danger": danger}


# ------------------------------------------------------------------
# 模組層級按鈕樣式（初始化為 standard + light）
# ------------------------------------------------------------------

_btn_styles = _build_btn_qss(FONT_SIZE_PRESETS["standard"], LIGHT_THEME)
BTN_PRIMARY = _btn_styles["primary"]
BTN_SECONDARY = _btn_styles["secondary"]
BTN_DANGER = _btn_styles["danger"]

# ------------------------------------------------------------------
# Log level 色彩（HTML 用）— 黑暗模式下微調對比
# ------------------------------------------------------------------


def _log_colors(is_dark_mode: bool) -> dict[str, str]:
    if is_dark_mode:
        return {
            "debug": "#9AA0A6",
            "info": "#4ADE80",    # 更亮的綠
            "warn": "#FACC00",
            "error": "#F87171",   # 更亮的紅
            "fatal": "#EF4444",
        }
    return {
        "debug": GREY_DARK,
        "info": SUCCESS,
        "warn": WARNING,
        "error": ERROR,
        "fatal": "#DC3545",
    }


LOG_COLORS = _log_colors(False)


# ------------------------------------------------------------------
# 套用樣式
# ------------------------------------------------------------------


def apply_brand_style(app, font_size_key: str = "standard", theme_key: str = "light") -> None:
    """套用品牌 QSS 到 QApplication。

    font_size_key: "standard" / "large" / "xlarge"
    theme_key:     "light" / "dark"（"system" 請先用 resolve_theme 轉換）
    """
    global _current_sizes, _current_theme, _current_theme_key
    global BTN_PRIMARY, BTN_SECONDARY, BTN_DANGER, LOG_COLORS
    global BG, SURFACE, BORDER, TEXT, TEXT_MUTED

    if font_size_key not in FONT_SIZE_PRESETS:
        font_size_key = "standard"
    if theme_key not in ("light", "dark"):
        theme_key = "light"

    _current_sizes = FONT_SIZE_PRESETS[font_size_key]
    _current_theme_key = theme_key
    _current_theme = DARK_THEME if theme_key == "dark" else LIGHT_THEME

    # 更新便利別名
    BG = _current_theme["bg"]
    SURFACE = _current_theme["surface"]
    BORDER = _current_theme["border"]
    TEXT = _current_theme["text"]
    TEXT_MUTED = _current_theme["text_muted"]

    app.setStyleSheet(_build_app_qss(_current_sizes, _current_theme))

    btns = _build_btn_qss(_current_sizes, _current_theme)
    BTN_PRIMARY = btns["primary"]
    BTN_SECONDARY = btns["secondary"]
    BTN_DANGER = btns["danger"]

    LOG_COLORS = _log_colors(theme_key == "dark")
