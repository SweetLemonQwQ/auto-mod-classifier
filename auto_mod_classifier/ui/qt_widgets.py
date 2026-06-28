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
    ACCENT_COLOR,
    ACCENT_SOFT_COLOR,
    BG_COLOR,
    BORDER_COLOR,
    ERROR_COLOR,
    MUTED_TEXT_COLOR,
    SURFACE_ALT_COLOR,
    SURFACE_COLOR,
    TEXT_COLOR,
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
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(16)
        self.container_layout = layout

        header = QWidget(content)
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)

        title_label = TitleLabel(title, header)
        subtitle_label = BodyLabel(subtitle, header)
        subtitle_label.setWordWrap(True)
        title_label.setStyleSheet(f"color: {TEXT_COLOR}; background: transparent;")
        subtitle_label.setStyleSheet(f"color: {MUTED_TEXT_COLOR}; background: transparent;")
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        layout.addWidget(header)

    def scroll_to_top(self) -> None:
        scrollbar = self.verticalScrollBar()
        if isinstance(scrollbar, QScrollBar):
            scrollbar.setValue(0)


class MetricCard(QFrame):
    """紧凑数字卡片，只展示一个重点指标。"""

    def __init__(self, title: str, value: str, note: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._animations: List[QPropertyAnimation] = []
        apply_card_style(self, "metric")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)

        caption = BodyLabel(title, self)
        caption.setWordWrap(True)
        caption.setStyleSheet(f"color: {MUTED_TEXT_COLOR}; background: transparent;")
        layout.addWidget(caption)

        self.value_label = TitleLabel(value, self)
        self.value_label.setStyleSheet(f"color: {TEXT_COLOR}; background: transparent;")
        layout.addWidget(self.value_label)

        self.note_label = BodyLabel(note, self)
        self.note_label.setWordWrap(True)
        self.note_label.setStyleSheet(f"color: {MUTED_TEXT_COLOR}; background: transparent;")
        layout.addWidget(self.note_label)

        layout.addStretch(1)

    def set_value(self, value: str) -> None:
        if self.value_label.text() != value:
            self.value_label.setText(value)
            _start_opacity_flash(self.value_label, self, self._animations)
            return
        self.value_label.setText(value)

    def set_note(self, note: str) -> None:
        self.note_label.setText(note)


class StageBoard(QFrame):
    """阶段时间线，跟随真实状态和日志推进。"""

    def __init__(self, title: str, stages: List[tuple[str, str]], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._animations: List[QPropertyAnimation] = []
        self.setObjectName("stageBoard")
        self.setStyleSheet(
            f"""
            QWidget#stageBoard {{
                background-color: {SURFACE_COLOR};
                border: 1px solid {BORDER_COLOR};
                border-radius: 8px;
            }}
            """
        )
        install_shadow(self)

        self.stage_order = [key for key, _ in stages]
        self.stage_rows: Dict[str, Dict[str, QLabel | QWidget]] = {}
        self.stage_details: Dict[str, str] = {}
        self.current_stage_key: Optional[str] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title_label = StrongBodyLabel(title, self)
        title_label.setStyleSheet(f"color: {TEXT_COLOR}; background: transparent;")
        layout.addWidget(title_label)

        for stage_key, stage_title in stages:
            row = QWidget(self)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(12, 10, 12, 10)
            row_layout.setSpacing(10)

            dot_label = QLabel("●", row)
            dot_label.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
            dot_label.setFixedWidth(14)
            row_layout.addWidget(dot_label, 0, Qt.AlignTop)

            text_column = QVBoxLayout()
            text_column.setContentsMargins(0, 0, 0, 0)
            text_column.setSpacing(3)

            title_widget = QLabel(stage_title, row)
            detail_widget = QLabel("", row)
            detail_widget.setWordWrap(True)
            text_column.addWidget(title_widget)
            text_column.addWidget(detail_widget)
            row_layout.addLayout(text_column, 1)

            self.stage_rows[stage_key] = {
                "container": row,
                "dot": dot_label,
                "title": title_widget,
                "detail": detail_widget,
            }
            layout.addWidget(row)

        layout.addStretch(1)
        self.reset()

    def reset(self) -> None:
        self.stage_details.clear()
        self.current_stage_key = None
        for index, stage_key in enumerate(self.stage_order):
            detail = "等待开始" if index == 0 else ""
            self.stage_details[stage_key] = detail
            self._apply_state(stage_key, "pending", detail)

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
            else:
                self._apply_state(key, "pending", self.stage_details.get(key, ""))

    def finish(self, detail: str = "已完成") -> None:
        for stage_key in self.stage_order[:-1]:
            self._apply_state(stage_key, "done", self.stage_details.get(stage_key, "已完成"))
        final_key = self.stage_order[-1]
        self.stage_details[final_key] = detail
        self._apply_state(final_key, "done", detail)
        self.current_stage_key = final_key

    def fail(self, detail: str) -> None:
        stage_key = self.current_stage_key or self.stage_order[0]
        current_index = self.stage_order.index(stage_key)
        for index, key in enumerate(self.stage_order):
            if index < current_index:
                self._apply_state(key, "done", self.stage_details.get(key, "已完成"))
            elif index == current_index:
                self._apply_state(key, "error", detail)
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
            dot_color = ACCENT_COLOR
            title_color = TEXT_COLOR
            detail_color = TEXT_COLOR
            row_background = ACCENT_SOFT_COLOR
            row_border = ACCENT_COLOR
        elif state == "done":
            dot_color = ACCENT_COLOR
            title_color = TEXT_COLOR
            detail_color = MUTED_TEXT_COLOR
            row_background = SURFACE_ALT_COLOR
            row_border = BORDER_COLOR
        elif state == "error":
            dot_color = ERROR_COLOR
            title_color = TEXT_COLOR
            detail_color = ERROR_COLOR
            row_background = "#30191B"
            row_border = ERROR_COLOR
        else:
            dot_color = BORDER_COLOR
            title_color = MUTED_TEXT_COLOR
            detail_color = MUTED_TEXT_COLOR
            row_background = "transparent"
            row_border = "transparent"

        container.setStyleSheet(
            f"""
            background-color: {row_background};
            border: 1px solid {row_border};
            border-radius: 8px;
            """
        )
        dot.setStyleSheet(f"color: {dot_color}; background: transparent; font-size: 14px;")
        title.setStyleSheet(f"color: {title_color}; background: transparent; font-size: 13px; font-weight: 600;")
        detail_label.setStyleSheet(f"color: {detail_color}; background: transparent; font-size: 12px;")
        detail_label.setText(detail)
        _start_opacity_flash(container, self, self._animations, start=0.7)


def build_tab_host(parent: QWidget, tabs: List[tuple[str, str, QWidget]]) -> tuple[QWidget, SegmentedWidget, QStackedWidget]:
    host = QWidget(parent)
    layout = QVBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(12)

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
    table.setMinimumHeight(320)
    table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
    table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
    table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
    table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
    table.setStyleSheet(
        f"""
        background-color: {SURFACE_ALT_COLOR};
        color: {TEXT_COLOR};
        border: 1px solid {BORDER_COLOR};
        border-radius: 8px;
        gridline-color: {BORDER_COLOR};
        """
    )
    return table


def populate_result_row(table: TableWidget, row_index: int, values: List[str]) -> None:
    for column_index, value in enumerate(values):
        item = QTableWidgetItem(value)
        item.setToolTip(value)
        item.setForeground(QBrush(QColor(TEXT_COLOR)))
        table.setItem(row_index, column_index, item)
