from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout

from client.services.auth import AuthService
from client.ui.components import Avatar, SecondaryButton, SectionTitle
from client.ui.dialogs import ProfileDialog
from client.ui.error_handler import handle_api_error

from .base_page import BasePage


class SettingsPage(BasePage):
    theme_toggled = Signal()

    def __init__(
        self,
        user: dict | None = None,
        auth_service: AuthService | None = None,
        parent=None,
    ):
        super().__init__("Настройки", "Профиль и цветовая тема")
        self.auth_service = auth_service
        self._build_profile(user)
        self._build_appearance()

    def _section(self, title: str) -> QVBoxLayout:
        from PySide6.QtWidgets import QFrame

        card = QFrame()
        card.setProperty("component", "card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)
        layout.addWidget(SectionTitle(title))
        self.content_layout.addWidget(card)
        return layout

    def _build_profile(self, user: dict | None):
        layout = self._section("Профиль")
        row = QHBoxLayout()
        row.setSpacing(14)
        self.profile_avatar = Avatar("", size=56)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        self.profile_name = QLabel()
        self.profile_name.setProperty("role", "card-title")
        self.profile_email = QLabel()
        self.profile_email.setProperty("role", "muted")
        text_layout.addWidget(self.profile_name)
        text_layout.addWidget(self.profile_email)
        row.addWidget(self.profile_avatar)
        row.addLayout(text_layout)
        row.addStretch()

        edit_button = SecondaryButton("Изменить профиль")
        edit_button.clicked.connect(self.edit_profile)
        row.addWidget(edit_button)
        layout.addLayout(row)
        self.set_user(user)

    def _build_appearance(self):
        layout = self._section("Цветовая тема")
        row = QHBoxLayout()
        description = QLabel("Выберите светлое или тёмное оформление")
        description.setProperty("role", "muted")
        button = SecondaryButton("Переключить тему")
        button.clicked.connect(self.theme_toggled.emit)
        row.addWidget(description, 1)
        row.addWidget(button)
        layout.addLayout(row)

    def set_user(self, user: dict | None):
        user = user or {}
        name = user.get("nick_name") or "Гость"
        self.profile_avatar.set_name(name)
        self.profile_name.setText(name)
        self.profile_email.setText(user.get("email") or "Нет данных")

    def edit_profile(self):
        if self.auth_service is None:
            return
        dialog = ProfileDialog(self.auth_service.user or {}, self)
        if dialog.exec() != ProfileDialog.DialogCode.Accepted:
            return
        try:
            user = self.auth_service.update_profile(**dialog.values())
        except Exception as error:
            handle_api_error(error, self)
            return
        self.set_user(user)

