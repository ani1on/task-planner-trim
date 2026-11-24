from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from client.api.mapper import format_relative
from client.api.models import Comment, Member
from client.services.comments import CommentService
from client.ui.components import PrimaryButton


def _clear(layout):
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()


def _muted(text: str) -> QLabel:
    label = QLabel(text)
    label.setProperty("role", "muted")
    return label


def _icon_button(text: str, tooltip: str) -> QPushButton:
    button = QPushButton(text)
    button.setProperty("icon", "true")
    button.setToolTip(tooltip)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setFixedSize(26, 26)
    return button


class CommentsSection(QWidget):
    """Список комментариев к задаче с добавлением, редактированием и удалением."""

    def __init__(
        self,
        comment_service: CommentService,
        task_id: int,
        members: list[Member],
        current_user_id: int | None,
        parent=None,
    ):
        super().__init__(parent)
        self.comment_service = comment_service
        self.task_id = task_id
        self.current_user_id = current_user_id
        self.authors = {member.user_id: member.nick_name for member in members}

        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(8)
        self.error_label = QLabel()
        self.error_label.setProperty("role", "form-error")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        self.root_layout.addWidget(self.error_label)

        self.list_layout = QVBoxLayout()
        self.list_layout.setSpacing(10)
        self.input = QPlainTextEdit()
        self.input.setPlaceholderText("Написать комментарий")
        self.input.setFixedHeight(72)
        send_button = PrimaryButton("Отправить")
        send_button.clicked.connect(self.add)

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(self.input, 1)
        row.addWidget(send_button, 0, Qt.AlignmentFlag.AlignBottom)
        self.root_layout.addLayout(self.list_layout)
        self.root_layout.addLayout(row)
        self.reload()

    def reload(self):
        self.error_label.clear()
        self.error_label.hide()
        _clear(self.list_layout)
        try:
            comments = self.comment_service.list(self.task_id)
        except Exception as error:
            self._show_error(error)
            return
        if not comments:
            self.list_layout.addWidget(_muted("Комментариев пока нет"))
            return
        for comment in comments:
            self.list_layout.addWidget(self._card(comment))

    def _card(self, comment: Comment) -> QFrame:
        frame = QFrame()
        frame.setProperty("component", "card")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        header = QHBoxLayout()
        header.setSpacing(8)
        author = QLabel(self.authors.get(
            comment.author_id, f"Пользователь #{comment.author_id}"
        ))
        author.setProperty("role", "task-title")
        moment = QLabel(format_relative(comment.created_at))
        moment.setProperty("role", "muted")
        header.addWidget(author)
        header.addWidget(moment)
        header.addStretch()

        if self.current_user_id == comment.author_id:
            content = QPlainTextEdit(comment.content)
            content.setFixedHeight(72)
            edit = _icon_button("✓", "Сохранить комментарий")
            edit.clicked.connect(
                lambda _=False, comment_id=comment.id, editor=content:
                    self.edit(comment_id, editor)
            )
            remove = _icon_button("×", "Удалить комментарий")
            remove.clicked.connect(
                lambda _=False, comment_id=comment.id: self.remove(comment_id)
            )
            header.addWidget(edit)
            header.addWidget(remove)
        else:
            content = QLabel(comment.content)
            content.setWordWrap(True)
        layout.addLayout(header)
        layout.addWidget(content)
        return frame

    def add(self):
        content = self.input.toPlainText().strip()
        if not content:
            return
        try:
            self.comment_service.create(self.task_id, content)
        except Exception as error:
            self._show_error(error)
            return
        self.input.clear()
        self.reload()

    def edit(self, comment_id: int, editor: QPlainTextEdit):
        content = editor.toPlainText().strip()
        if not content:
            return
        try:
            self.comment_service.update(comment_id, content)
        except Exception as error:
            self._show_error(error)
            return
        self.reload()

    def remove(self, comment_id: int):
        try:
            self.comment_service.delete(comment_id)
        except Exception as error:
            self._show_error(error)
            return
        self.reload()

    def _show_error(self, error: Exception):
        from client.ui.error_handler import error_message

        self.error_label.setText(error_message(error))
        self.error_label.show()
