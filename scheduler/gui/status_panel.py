"""
gui/status_panel.py - 可編輯城市狀態卡片

每個城市一張 QGroupBox，包含：
  - 啟用 checkbox + 間隔輸入 + 單位
  - 車位數輸入欄位 + 單位（依縣市外掛的 value_fields 動態生成）
  - 上次/下次上傳時間（唯讀）
  - 上傳結果（唯讀）
  - 「立即上傳」與「儲存排程」按鈕

卡片內容全部來自 scheduler.cities 註冊表，本檔不含縣市專屬判斷。
所有數字輸入使用 QLineEdit + QIntValidator，不顯示上下箭頭按鈕。
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from scheduler import cities

from scheduler.gui import brand

_INPUT_WIDTH = 70


def _make_form_label(text: str) -> QLabel:
    """表單欄位 label（強對比 + 粗體）。"""
    label = QLabel(text)
    label.setObjectName("formLabel")
    return label


def _make_unit_label(text: str) -> QLabel:
    """單位文字 label（次要色）。"""
    label = QLabel(text)
    label.setObjectName("mutedLabel")
    return label


def _make_int_input(min_val: int = 0, max_val: int = 9999, width: int = _INPUT_WIDTH) -> QLineEdit:
    """建立純數字輸入欄（無上下按鈕，寬度隨字級調整）。"""
    edit = QLineEdit("0")
    edit.setValidator(QIntValidator(min_val, max_val))
    s = brand.get_font_sizes()
    scale = s['input'] / 13.0
    edit.setFixedWidth(int(width * scale))
    edit.setAlignment(Qt.AlignmentFlag.AlignRight)
    return edit


class EditableCityCard(QGroupBox):
    """單一城市可編輯狀態卡片（欄位由縣市外掛宣告）。"""

    config_save_requested = Signal(str, dict)  # city_key, values_dict
    upload_now_requested = Signal(str, dict)  # city_key, values_dict（儲存+上傳）

    def __init__(self, city_key: str, parent=None):
        plugin = cities.get_city(city_key)
        display_name = plugin.display_name if plugin else city_key
        super().__init__(display_name, parent)
        self._city_key = city_key
        self._plugin = plugin

        default_enabled = plugin.default_enabled if plugin else False
        default_interval = plugin.default_interval if plugin else 10

        layout = QVBoxLayout()
        layout.setSpacing(6)

        # 第一行：定時執行 + 間隔 + 上次/下次
        top_row = QHBoxLayout()
        self._enabled_cb = QCheckBox("定時執行")
        self._enabled_cb.setCursor(Qt.CursorShape.PointingHandCursor)
        # 依縣市外掛的預設決定是否啟用定時上傳
        if default_enabled:
            self._enabled_cb.setChecked(True)
        self._enabled_cb.toggled.connect(self._on_enabled_toggled)
        top_row.addWidget(self._enabled_cb)

        top_row.addSpacing(12)

        top_row.addWidget(_make_form_label("間隔"))
        self._interval_input = _make_int_input(1, 60, 40)
        self._interval_input.setText(str(default_interval))
        top_row.addWidget(self._interval_input)
        top_row.addWidget(_make_unit_label("分鐘"))

        top_row.addSpacing(12)

        # 上次/下次時間（放在間隔後方）
        self._last_upload = QLabel("上次：—")
        self._last_upload.setObjectName("statusLabel")
        top_row.addWidget(self._last_upload)

        top_row.addSpacing(8)

        self._next_upload = QLabel("下次：—")
        self._next_upload.setObjectName("statusLabel")
        top_row.addWidget(self._next_upload)

        top_row.addStretch()
        layout.addLayout(top_row)

        # 車位數欄位（依縣市外掛 value_fields 動態建立，每列最多兩欄）
        self._value_inputs: dict[str, QLineEdit] = {}
        # 允許留空的欄位：key → 留空時送出的值（UI 上留空顯示，不對使用者揭露此值）
        self._blank_values: dict[str, int] = {}
        # 以 grid 排版：label 靠右緊貼 input，兩組之間留間距，多餘寬度推到最右欄
        value_fields = plugin.value_fields if plugin else []
        grid = QGridLayout()
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(6)
        for i, vf in enumerate(value_fields):
            row, pair = divmod(i, 2)
            col = pair * 3  # 每組佔 label / input / 間距 三欄
            label, edit = self._make_field(vf.key, vf.label, vf.blank_value)
            grid.addWidget(label, row, col, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            grid.addWidget(edit, row, col + 1)
        grid.setColumnMinimumWidth(2, 24)
        grid.setColumnStretch(5, 1)
        layout.addLayout(grid)

        # 上傳結果 / 提示訊息
        self._result_label = QLabel("")
        self._result_label.setWordWrap(True)
        self._result_label.setObjectName("statusLabel")
        layout.addWidget(self._result_label)

        # 不預設定時的縣市（手動上傳為主），啟動時顯示提示
        if not default_enabled:
            self._result_label.setText("提示：設定車位數後請點擊「立即上傳」按鈕")

        # 初始化時依 checkbox 狀態隱藏「下次」
        self._on_enabled_toggled(self._enabled_cb.isChecked())

        # 按鈕列（靠右顯示）
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._upload_btn = QPushButton("立即上傳")
        self._upload_btn.setStyleSheet(brand.BTN_SECONDARY)
        self._upload_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._upload_btn.clicked.connect(self._on_upload)
        btn_row.addWidget(self._upload_btn)

        self._save_btn = QPushButton("儲存設定")
        self._save_btn.setStyleSheet(brand.BTN_PRIMARY)
        self._save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(self._save_btn)

        layout.addLayout(btn_row)

        self.setLayout(layout)
        self.setMinimumWidth(240)

    def _on_enabled_toggled(self, checked: bool) -> None:
        """切換 checkbox 時顯示/隱藏「下次」。"""
        self._next_upload.setVisible(checked)

    def _make_field(
        self, key: str, label_text: str, blank_value: int | None = None
    ) -> tuple[QLabel, QLineEdit]:
        """建立一組：label + 輸入欄（由呼叫端放入 grid）。"""
        label = _make_form_label(label_text)

        edit = _make_int_input()
        if blank_value is not None:
            edit.setText("")
            edit.setPlaceholderText("可留空")
            edit.setToolTip("沒有此車種請留空")
            self._blank_values[key] = blank_value
        self._value_inputs[key] = edit

        return label, edit

    # ------------------------------------------------------------------
    # Config ↔ UI
    # ------------------------------------------------------------------

    def _get_int(self, edit: QLineEdit) -> int:
        """安全取得 QLineEdit 的整數值。"""
        text = edit.text().strip()
        if not text:
            return 0
        try:
            return int(text)
        except ValueError:
            return 0

    def update_config(self, config: dict | None) -> None:
        """從 schedule.json 載入設定到 UI。"""
        if not config:
            self._enabled_cb.setChecked(False)
            return

        self._enabled_cb.setChecked(config.get("enabled", False))
        self._interval_input.setText(str(config.get("intervalMinutes", 10)))

        values = config.get("values", {})
        for key, edit in self._value_inputs.items():
            value = values.get(key, self._blank_values.get(key, 0))
            if key in self._blank_values and value == self._blank_values[key]:
                edit.setText("")
            else:
                edit.setText(str(value))

    def _collect_values(self) -> dict:
        """從 UI 收集目前的設定值。"""
        values = {
            key: (
                self._blank_values[key]
                if key in self._blank_values and not edit.text().strip()
                else self._get_int(edit)
            )
            for key, edit in self._value_inputs.items()
        }
        return {
            "enabled": self._enabled_cb.isChecked(),
            "intervalMinutes": self._get_int(self._interval_input),
            "values": values,
        }

    def _on_save(self) -> None:
        self.config_save_requested.emit(self._city_key, self._collect_values())

    def _on_upload(self) -> None:
        """立即上傳：帶目前 UI 值，由 main.py 統一儲存+重載+上傳。"""
        self.upload_now_requested.emit(self._city_key, self._collect_values())

    # ------------------------------------------------------------------
    # Status updates
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_time(iso_str: str) -> str:
        """從 ISO 時間字串擷取 HH:MM:SS。"""
        t_idx = iso_str.find("T")
        if t_idx == -1:
            return iso_str
        time_part = iso_str[t_idx + 1:]
        return time_part[:8]

    def update_status(self, status: dict) -> None:
        """更新執行狀態。"""
        last = status.get("lastUpload")
        if last:
            self._last_upload.setText(f"上次：{self._extract_time(last)}")

        next_t = status.get("nextUpload")
        if next_t:
            self._next_upload.setText(f"下次：{self._extract_time(next_t)}")

        success = status.get("lastSuccess")
        message = status.get("lastMessage", "")
        if success is True:
            self._result_label.setText(f"✓ {message}")
            self._result_label.setObjectName("statusLabelSuccess")
        elif success is False:
            self._result_label.setText(f"✗ {message}")
            self._result_label.setObjectName("statusLabelError")
        # 重新套用 QSS（objectName 變更後需要）
        self._result_label.style().unpolish(self._result_label)
        self._result_label.style().polish(self._result_label)


class StatusPanel(QWidget):
    """狀態面板，水平排列可編輯城市卡片。"""

    config_save_requested = Signal(str, dict)  # city_key, values_dict
    upload_now_requested = Signal(str, dict)  # city_key, values_dict（儲存+上傳）

    def __init__(self, visible_cities: list[str], parent=None):
        super().__init__(parent)
        self._cards: dict[str, EditableCityCard] = {}

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        for city_key in visible_cities:
            card = EditableCityCard(city_key)
            card.config_save_requested.connect(self.config_save_requested)
            card.upload_now_requested.connect(self.upload_now_requested)
            self._cards[city_key] = card
            layout.addWidget(card)

        self.setLayout(layout)

    def update_config(self, schedule: dict) -> None:
        for city_key, card in self._cards.items():
            card.update_config(schedule.get(city_key))

    def update_city_status(self, target: str, status: dict) -> None:
        if target in self._cards:
            self._cards[target].update_status(status)
