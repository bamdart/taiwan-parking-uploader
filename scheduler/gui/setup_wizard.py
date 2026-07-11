"""
gui/setup_wizard.py - 首次設定精靈

兩步驟 QDialog：
  Step 1 — 選擇縣市（Radio buttons，來自 scheduler.cities 註冊表）
  Step 2 — 輸入帳密（依所選縣市外掛的 credential_fields 動態顯示欄位）

完成後寫入 .env（ACTIVE_CITY + 帳密），回傳 Accepted。
本檔不含任何縣市專屬欄位，新增縣市不需改動此檔。
"""

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from scheduler import branding, cities
from scheduler.gui import brand


class SetupWizard(QDialog):
    """首次設定精靈（縣市清單與欄位皆來自外掛註冊表）。"""

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self._config = config_manager

        # 已註冊縣市（順序即顯示順序）
        self._plugins = cities.all_cities()

        self.setWindowTitle(f"{branding.APP_NAME} — 首次設定")
        self.setFixedSize(480, 460)

        # 視窗圖示（從內嵌 base64）
        from scheduler.gui._favicon import favicon_qicon
        self.setWindowIcon(favicon_qicon())

        # 頂部品牌裝飾條（青色）
        accent_bar = QFrame()
        accent_bar.setFixedHeight(3)
        accent_bar.setStyleSheet(f"background: {brand.SECONDARY};")

        # 每個縣市的帳密欄位 widget 參照
        # city_key -> {"group": QGroupBox, "creds": {name: QLineEdit}, "endpoint": QLineEdit|None}
        self._forms: dict[str, dict] = {}

        # Stacked widget
        self._stack = QStackedWidget()
        self._page_city = self._build_city_page()
        self._page_creds = self._build_creds_page()
        self._stack.addWidget(self._page_city)
        self._stack.addWidget(self._page_creds)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(accent_bar)
        inner = QVBoxLayout()
        inner.setContentsMargins(24, 16, 24, 16)
        inner.addWidget(self._stack)
        layout.addLayout(inner)
        self.setLayout(layout)

    # ------------------------------------------------------------------
    # Step 1 — 選擇縣市
    # ------------------------------------------------------------------

    def _build_city_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(16)

        # 標題
        title = QLabel(f"歡迎使用 {branding.APP_NAME}")
        title.setObjectName("wizardTitle")
        title.setWordWrap(True)
        layout.addWidget(title)

        subtitle = QLabel("請選擇要對接的縣市，稍後設定 API 帳密")
        subtitle.setObjectName("wizardSubtitle")
        layout.addWidget(subtitle)

        layout.addSpacing(8)

        # Radio buttons（每個已註冊縣市一個）
        group = QGroupBox("選擇縣市")
        group_layout = QVBoxLayout()
        group_layout.setSpacing(12)

        self._city_group = QButtonGroup(self)
        self._city_group.setExclusive(True)

        for index, plugin in enumerate(self._plugins):
            radio = QRadioButton(plugin.display_name)
            radio.setCursor(Qt.CursorShape.PointingHandCursor)
            group_layout.addWidget(radio)
            self._city_group.addButton(radio, index)

        # 預設選第一個縣市，再 connect signal（避免初始化時提前觸發）
        first_btn = self._city_group.button(0)
        if first_btn:
            first_btn.setChecked(True)
        self._city_group.buttonToggled.connect(self._on_city_radio_toggled)

        group.setLayout(group_layout)
        layout.addWidget(group)

        layout.addStretch()

        # 按鈕
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_next = QPushButton("下一步")
        btn_next.setStyleSheet(brand.BTN_PRIMARY)
        btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_next.clicked.connect(self._go_to_creds)
        btn_row.addWidget(btn_next)
        layout.addLayout(btn_row)

        page.setLayout(layout)
        return page

    # ------------------------------------------------------------------
    # Step 2 — 輸入帳密
    # ------------------------------------------------------------------

    def _build_creds_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(16)

        title = QLabel("設定 API 帳密")
        title.setObjectName("wizardTitle")
        layout.addWidget(title)

        self._creds_subtitle = QLabel("")
        self._creds_subtitle.setObjectName("wizardSubtitle")
        self._creds_subtitle.setWordWrap(True)
        layout.addWidget(self._creds_subtitle)

        layout.addSpacing(4)

        # 為每個縣市建立一組表單（依 credential_fields + endpoint）
        for plugin in self._plugins:
            group = QGroupBox(plugin.display_name)
            form = QFormLayout()

            cred_edits: dict[str, QLineEdit] = {}
            for field in plugin.credential_fields:
                edit = QLineEdit()
                edit.setPlaceholderText(field.label)
                if field.secret:
                    edit.setEchoMode(QLineEdit.EchoMode.Password)
                form.addRow(field.label, edit)
                cred_edits[field.name] = edit

            endpoint_edit = None
            if plugin.endpoint_env_key:
                endpoint_edit = QLineEdit()
                endpoint_edit.setText(plugin.default_endpoint)
                endpoint_edit.setPlaceholderText("API Endpoint")
                form.addRow("Endpoint", endpoint_edit)

            group.setLayout(form)
            layout.addWidget(group)

            self._forms[plugin.key] = {
                "group": group,
                "creds": cred_edits,
                "endpoint": endpoint_edit,
            }

        layout.addStretch()

        # 按鈕
        btn_row = QHBoxLayout()
        btn_back = QPushButton("上一步")
        btn_back.setStyleSheet(brand.BTN_SECONDARY)
        btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_back.clicked.connect(lambda: self._stack.setCurrentIndex(0))
        btn_row.addWidget(btn_back)
        btn_row.addStretch()
        btn_finish = QPushButton("完成設定")
        btn_finish.setStyleSheet(brand.BTN_PRIMARY)
        btn_finish.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_finish.clicked.connect(self._on_finish)
        btn_row.addWidget(btn_finish)
        layout.addLayout(btn_row)

        page.setLayout(layout)
        return page

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _selected_plugin(self):
        """回傳目前選中的縣市外掛。"""
        index = self._city_group.checkedId()
        if 0 <= index < len(self._plugins):
            return self._plugins[index]
        return self._plugins[0] if self._plugins else None

    def _on_city_radio_toggled(self, button, checked: bool) -> None:
        """radio 切換時即時更新帳密表單顯示。"""
        if not checked:
            return  # 只處理「被選中」事件，忽略「被取消」
        self._sync_creds_form()

    def _sync_creds_form(self) -> None:
        """依目前選擇的縣市，更新帳密頁的表單可見性與副標題。"""
        # 防禦：表單可能尚未建立（初始化時 signal 提前觸發）
        if not self._forms:
            return

        plugin = self._selected_plugin()
        if not plugin:
            return

        for key, widgets in self._forms.items():
            widgets["group"].setVisible(key == plugin.key)

        self._creds_subtitle.setText(
            f"請輸入{plugin.display_name}提供的 API 帳密"
        )

    def _go_to_creds(self) -> None:
        self._sync_creds_form()
        self._stack.setCurrentIndex(1)

    # ------------------------------------------------------------------
    # Finish
    # ------------------------------------------------------------------

    def _on_finish(self) -> None:
        plugin = self._selected_plugin()
        if not plugin:
            return

        widgets = self._forms[plugin.key]
        cred_edits: dict[str, QLineEdit] = widgets["creds"]

        # 驗證所有帳密欄位皆已填
        missing = [
            field.label
            for field in plugin.credential_fields
            if not cred_edits[field.name].text().strip()
        ]
        if missing:
            QMessageBox.warning(
                self, "欄位不完整", "請填入：" + "、".join(missing)
            )
            return

        # 組裝 .env values
        env_values: dict[str, str] = {"ACTIVE_CITY": plugin.key}
        for field in plugin.credential_fields:
            env_values[field.env_key] = cred_edits[field.name].text().strip()

        endpoint_edit = widgets["endpoint"]
        if endpoint_edit is not None and plugin.endpoint_env_key:
            endpoint = endpoint_edit.text().strip()
            if endpoint:
                env_values[plugin.endpoint_env_key] = endpoint

        # 避免舊的 .env.local 殘留 ACTIVE_CITY 覆蓋新寫入的 .env
        env_local = os.path.join(self._config.base_dir, ".env.local")
        if os.path.isfile(env_local):
            try:
                os.remove(env_local)
            except OSError:
                pass

        # 寫入 .env 並重載
        self._config.save_env(env_values)
        self._config.reload_env()

        # 刪除舊 schedule.json 並清空記憶體中的 schedule
        # 不自動建立預設 schedule.json，等使用者在主視窗填完車位數按「儲存設定」後再寫入
        schedule_path = self._config.schedule_path
        if os.path.isfile(schedule_path):
            try:
                os.remove(schedule_path)
            except OSError:
                pass
        self._config._schedule = None

        self.accept()
