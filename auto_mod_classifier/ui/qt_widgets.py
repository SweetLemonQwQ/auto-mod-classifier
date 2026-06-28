from __future__ import annotations

from typing import Dict, List, Optional

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QScrollBar,
    QSizePolicy,
    QStackedWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    ScrollArea,
    SegmentedWidget,
    StrongBodyLabel,
    TableWidget,
    TitleLabel,
)

from .qt_theme import (
    ACCENT_SOFT_COLOR,
    ACCENT_COLOR,
    BG_COLOR,
    ERROR_COLOR,
    IDLE_COLOR,
    MUTED_TEXT_COLOR,
    RUNNING_COLOR,
    SECONDARY_TEXT_COLOR,
    SUCCESS_COLOR,
    TEXT_COLOR,
    WARNING_COLOR,
    WEAK_BORDER_COLOR,
    apply_card_style,
    install_shadow,
)


def _start_opacity_flash(widget: QWidget, owner: QWidget, store: List[QPropertyAnimation], *, start: float = 0.45) -> None:
    effect = widget.graphicsEffect()
    if not isinstance(effect, QGraphicsOpacityEffect):
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
    effect.setOpacity(start)
    animation = QPropertyAnimation(effect, b"opacity", owner)
    animation.setDuration(180)
    animation.setStartValue(start)
    animation.setEndValue(1.0)
    animation.setEasingCurve(QEasingCurve.OutCubic)
    store.append(animation)

    def _cleanup() -> None:
        if animation in store:
            store.remove(animation)

    animation.finished.connect(_cleanup)
    animation.start()


class ScrollablePage(ScrollArea):
    """统一页面壳子，负责滚动和头部标题。"""

    def __init__(self, page_key: str, title: str, subtitle: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.page_key = page_key
        self.setObjectName(page_key)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.viewport().setStyleSheet(f"background-color: {BG_COLOR}; border: 0;")

        content = QWidget(self)
        content.setObjectName(f"{page_key}Content")
        content.setStyleSheet(f"background-color: {BG_COLOR};")
        self.setWidget(content)
        self.content = content

        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 16, 20, 20)
        layout.setSpacing(16)
        self.container_layout = layout

        header = QWidget(content)
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)

        title_label = TitleLabel(title, header)
        subtitle_label = BodyLabel(subtitle, header)
        subtitle_label.setWordWrap(True)
        title_label.setStyleSheet(f"color: {TEXT_COLOR}; background: transparent; font-size: 20px; font-weight: 600;")
        subtitle_label.setStyleSheet(f"color: {MUTED_TEXT_COLOR}; background: transparent; font-size: 12px;")
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        layout.addWidget(header)

    def scroll_to_top(self) -> None:
        scrollbar = self.verticalScrollBar()
        if isinstance(scrollbar, QScrollBar):
            scrollbar.setValue(0)


class TaskPage(QWidget):
    """固定首屏页面壳子，功能页不做整页纵向滚动。"""

    def __init__(self, page_key: str, title: str, subtitle: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.page_key = page_key
        self.setObjectName(page_key)
        self.setStyleSheet(f"background-color: {BG_COLOR};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 14, 20, 18)
        layout.setSpacing(12)
        self.container_layout = layout

        header = QWidget(self)
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)

        title_label = TitleLabel(title, header)
        title_label.setStyleSheet(f"color: {TEXT_COLOR}; background: transparent; font-size: 20px; font-weight: 600;")
        header_layout.addWidget(title_label)
        if subtitle:
            subtitle_label = BodyLabel(subtitle, header)
            subtitle_label.setWordWrap(True)
            subtitle_label.setStyleSheet(f"color: {MUTED_TEXT_COLOR}; background: transparent; font-size: 12px;")
            header_layout.addWidget(subtitle_label)
        layout.addWidget(header, 0)

    def scroll_to_top(self) -> None:
        pass


class StatusDot(QFrame):
    """状态圆点。颜色和文字一起使用，避免只靠颜色表达状态。"""

    STATE_COLORS = {
        "idle": IDLE_COLOR,
        "running": RUNNING_COLOR,
        "success": SUCCESS_COLOR,
        "warning": WARNING_COLOR,
        "error": ERROR_COLOR,
    }

    def __init__(self, parent: Optional[QWidget] = None, *, size: int = 9):
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, size)
        self.set_state("idle")

    def set_state(self, state: str) -> None:
        color = self.STATE_COLORS.get(state, IDLE_COLOR)
        alpha = 170 if state == "idle" else 255
        self.setStyleSheet(
            f"""
            background-color: {color};
            border: 1px solid rgba(241, 245, 249, {alpha});
            border-radius: {(self._size + 1) // 2}px;
            """
        )


class MetricCard(QFrame):
    """紧凑数字卡片，只展示一个重点指标。"""

    def __init__(
        self,
        title: str,
        value: str,
        note: str = "",
        parent: Optional[QWidget] = None,
        *,
        accent_color: str = ACCENT_COLOR,
    ):
        super().__init__(parent)
        self._animations: List[QPropertyAnimation] = []
        self._accent_color = accent_color
        apply_card_style(self, "metric")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        accent = QFrame(self)
        accent.setFixedHeight(3)
        accent.setStyleSheet(f"background-color: {accent_color}; border-radius: 2px;")
        layout.addWidget(accent)

        caption = BodyLabel(title, self)
        caption.setAlignment(Qt.AlignCenter)
        caption.setStyleSheet(f"color: {MUTED_TEXT_COLOR}; background: transparent; font-size: 12px;")

        self.value_label = TitleLabel(value, self)
        self.value_label.setAlignment(Qt.AlignCenter)
        self.value_label.setStyleSheet(f"color: {TEXT_COLOR}; background: transparent; font-size: 24px; font-weight: 700;")
        layout.addWidget(self.value_label, 0, Qt.AlignCenter)
        layout.addWidget(caption)

        self.note_label = BodyLabel(note, self)
        self.note_label.setAlignment(Qt.AlignCenter)
        self.note_label.setWordWrap(True)
        self.note_label.setStyleSheet(f"color: {MUTED_TEXT_COLOR}; background: transparent; font-size: 12px;")
        layout.addWidget(self.note_label)

        layout.addStretch(1)

        self.setMinimumHeight(108)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_value(self, value: str) -> None:
        if self.value_label.text() != value:
            self.value_label.setText(value)
            _start_opacity_flash(self.value_label, self, self._animations)
            return
        self.value_label.setText(value)

    def set_note(self, note: str) -> None:
        self.note_label.setText(note)


class StageBoard(QFrame):
    """横向阶段进度，跟随真实状态和日志推进。"""

    def __init__(self, title: str, stages: List[tuple[str, str]], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._animations: List[QPropertyAnimation] = []
        self.setObjectName("stageBoard")
        apply_card_style(self, "panel")
        install_shadow(self)

        self.stage_order = [key for key, _ in stages]
        self.stage_rows: Dict[str, Dict[str, QLabel | QWidget]] = {}
        self.stage_details: Dict[str, str] = {}
        self.current_stage_key: Optional[str] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        title_label = StrongBodyLabel(title, self)
        title_label.setStyleSheet(f"color: {TEXT_COLOR}; background: transparent; font-size: 14px; font-weight: 600;")
        layout.addWidget(title_label)

        track = QWidget(self)
        track_layout = QHBoxLayout(track)
        track_layout.setContentsMargins(0, 0, 0, 0)
        track_layout.setSpacing(8)
        layout.addWidget(track)

        for index, (stage_key, stage_title) in enumerate(stages, start=1):
            row = QWidget(track)
            row_layout = QVBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(6)

            dot_label = QLabel(str(index), row)
            dot_label.setAlignment(Qt.AlignCenter)
            dot_label.setFixedSize(24, 24)
            row_layout.addWidget(dot_label, 0, Qt.AlignHCenter)

            title_widget = QLabel(stage_title, row)
            title_widget.setAlignment(Qt.AlignCenter)
            title_widget.setWordWrap(True)
            detail_widget = QLabel("", row)
            detail_widget.hide()
            row_layout.addWidget(title_widget)
            row_layout.addWidget(detail_widget)

            self.stage_rows[stage_key] = {
                "container": row,
                "dot": dot_label,
                "title": title_widget,
                "detail": detail_widget,
            }
            track_layout.addWidget(row, 1)
            if index < len(stages):
                line_host = QWidget(track)
                line_host.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                line_host_layout = QVBoxLayout(line_host)
                line_host_layout.setContentsMargins(0, 11, 0, 0)
                line_host_layout.setSpacing(0)
                line = QFrame(line_host)
                line.setFixedHeight(2)
                line.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                line.setStyleSheet(f"background-color: {WEAK_BORDER_COLOR}; border: 0;")
                line_host_layout.addWidget(line)
                line_host_layout.addStretch(1)
                self.stage_rows[stage_key]["line"] = line
                track_layout.addWidget(line_host, 1)

        self.detail_label = BodyLabel("等待开始", self)
        self.detail_label.setWordWrap(True)
        self.detail_label.setStyleSheet(f"color: {MUTED_TEXT_COLOR}; background: transparent;")
        layout.addWidget(self.detail_label)
        self.reset()

    def reset(self) -> None:
        self.stage_details.clear()
        self.current_stage_key = None
        for index, stage_key in enumerate(self.stage_order):
            detail = "等待开始" if index == 0 else ""
            self.stage_details[stage_key] = detail
            self._apply_state(stage_key, "pending", detail)
        self.detail_label.setText("等待开始")

    def activate(self, stage_key: str, detail: str = "") -> None:
        if stage_key not in self.stage_rows:
            return
        self.current_stage_key = stage_key
        current_index = self.stage_order.index(stage_key)
        if detail:
            self.stage_details[stage_key] = detail

        for index, key in enumerate(self.stage_order):
            if index < current_index:
                self._apply_state(key, "done", self.stage_details.get(key, "已完成"))
            elif index == current_index:
                self._apply_state(key, "running", self.stage_details.get(key, detail))
                self.detail_label.setText(self.stage_details.get(key, detail) or "运行中")
            else:
                self._apply_state(key, "pending", self.stage_details.get(key, ""))

    def finish(self, detail: str = "已完成") -> None:
        for stage_key in self.stage_order[:-1]:
            self._apply_state(stage_key, "done", self.stage_details.get(stage_key, "已完成"))
        final_key = self.stage_order[-1]
        self.stage_details[final_key] = detail
        self._apply_state(final_key, "done", detail)
        self.detail_label.setText(detail)
        self.current_stage_key = final_key

    def fail(self, detail: str) -> None:
        stage_key = self.current_stage_key or self.stage_order[0]
        current_index = self.stage_order.index(stage_key)
        for index, key in enumerate(self.stage_order):
            if index < current_index:
                self._apply_state(key, "done", self.stage_details.get(key, "已完成"))
            elif index == current_index:
                self._apply_state(key, "error", detail)
                self.detail_label.setText(detail)
            else:
                self._apply_state(key, "pending", self.stage_details.get(key, ""))

    def _apply_state(self, stage_key: str, state: str, detail: str) -> None:
        row = self.stage_rows[stage_key]
        container = row["container"]
        dot = row["dot"]
        title = row["title"]
        detail_label = row["detail"]

        if not isinstance(container, QWidget) or not isinstance(dot, QLabel) or not isinstance(title, QLabel) or not isinstance(detail_label, QLabel):
            return

        if state == "running":
            dot_color = RUNNING_COLOR
            title_color = TEXT_COLOR
            detail_color = TEXT_COLOR
            dot_background = "rgba(52, 211, 153, 48)"
            line_color = RUNNING_COLOR
        elif state == "done":
            dot_color = SUCCESS_COLOR
            title_color = TEXT_COLOR
            detail_color = MUTED_TEXT_COLOR
            dot_background = ACCENT_SOFT_COLOR
            line_color = SUCCESS_COLOR
        elif state == "error":
            dot_color = ERROR_COLOR
            title_color = TEXT_COLOR
            detail_color = ERROR_COLOR
            dot_background = "rgba(248, 113, 113, 42)"
            line_color = ERROR_COLOR
        else:
            dot_color = IDLE_COLOR
            title_color = MUTED_TEXT_COLOR
            detail_color = MUTED_TEXT_COLOR
            dot_background = "rgba(100, 116, 139, 24)"
            line_color = WEAK_BORDER_COLOR

        container.setStyleSheet("background: transparent; border: 0;")
        dot.setStyleSheet(
            f"""
            color: {dot_color if state == "pending" else TEXT_COLOR};
            background-color: {dot_background};
            border: 1px solid {dot_color};
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            """
        )
        title.setStyleSheet(f"color: {title_color}; background: transparent; font-size: 12px; font-weight: 600;")
        detail_label.setStyleSheet(f"color: {detail_color}; background: transparent; font-size: 12px;")
        detail_label.setText(detail)
        line = row.get("line")
        if isinstance(line, QFrame):
            line.setStyleSheet(f"background-color: {line_color}; border: 0;")
        if state in {"running", "done", "error"}:
            _start_opacity_flash(dot, self, self._animations, start=0.65)


class ActionCard(QFrame):
    """首页大按钮卡片，用按钮承担明确点击目标。"""

    def __init__(
        self,
        title: str,
        description: str,
        button_text: str,
        parent: Optional[QWidget] = None,
        *,
        icon=None,
        primary: bool = False,
    ):
        super().__init__(parent)
        variant = "hero" if primary else "panel"
        apply_card_style(self, variant)
        self.setStyleSheet(
            self.styleSheet()
            + f"""
            QFrame#{variant}Card {{
                border: 1px solid {WEAK_BORDER_COLOR};
            }}
            QFrame#{variant}Card:hover {{
                border-color: rgba(52, 211, 153, 125);
            }}
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)
        if icon is not None:
            from qfluentwidgets import IconWidget

            icon_widget = IconWidget(icon, self)
            icon_widget.setFixedSize(22, 22)
            header_row.addWidget(icon_widget, 0, Qt.AlignTop)

        title_label = StrongBodyLabel(title, self)
        title_label.setStyleSheet(f"color: {TEXT_COLOR}; background: transparent; font-size: 14px; font-weight: 600;")
        header_row.addWidget(title_label, 1)
        layout.addLayout(header_row)

        desc_label = BodyLabel(description, self)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(f"color: {MUTED_TEXT_COLOR}; background: transparent; font-size: 12px;")
        layout.addWidget(desc_label)
        layout.addStretch(1)

        from qfluentwidgets import PrimaryPushButton, PushButton

        self.button = PrimaryPushButton(button_text, self) if primary else PushButton(button_text, self)
        self.button.setObjectName("smallButton")
        layout.addWidget(self.button, 0, Qt.AlignLeft)


def build_tab_host(parent: QWidget, tabs: List[tuple[str, str, QWidget]]) -> tuple[QWidget, SegmentedWidget, QStackedWidget]:
    host = QWidget(parent)
    layout = QVBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(10)

    segmented = SegmentedWidget(host)
    stacked = QStackedWidget(host)
    layout.addWidget(segmented, 0, Qt.AlignLeft)
    layout.addWidget(stacked, 1)

    for route_key, text, widget in tabs:
        stacked.addWidget(widget)
        segmented.addItem(route_key, text, onClick=lambda w=widget: stacked.setCurrentWidget(w))

    if tabs:
        segmented.setCurrentItem(tabs[0][0])
        stacked.setCurrentWidget(tabs[0][2])

    return host, segmented, stacked


def build_result_table(parent: QWidget) -> TableWidget:
    table = TableWidget(parent)
    table.setColumnCount(4)
    table.setHorizontalHeaderLabels(["文件名", "分类结果", "判定来源", "原因"])
    table.verticalHeader().setVisible(False)
    table.setEditTriggers(TableWidget.NoEditTriggers)
    table.setSelectionBehavior(TableWidget.SelectRows)
    table.setAlternatingRowColors(True)
    table.setWordWrap(False)
    table.setMinimumHeight(120)
    table.verticalHeader().setDefaultSectionSize(28)
    table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
    table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
    table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
    table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
    table.setStyleSheet(
        f"""
        background-color: #172033;
        alternate-background-color: #1C283B;
        color: {SECONDARY_TEXT_COLOR};
        border: 1px solid {WEAK_BORDER_COLOR};
        border-radius: 8px;
        gridline-color: rgba(71, 85, 105, 70);
        selection-background-color: rgba(52, 211, 153, 55);
        selection-color: {TEXT_COLOR};
        """
    )
    return table


def populate_result_row(table: TableWidget, row_index: int, values: List[str]) -> None:
    for column_index, value in enumerate(values):
        item = QTableWidgetItem(value)
        item.setToolTip(value)
        item.setForeground(QBrush(QColor(TEXT_COLOR)))
        table.setItem(row_index, column_index, item)
