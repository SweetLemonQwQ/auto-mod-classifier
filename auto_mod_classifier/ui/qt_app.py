from __future__ import annotations

import json
import os
import queue
import re
import shutil
import sys
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import qfluentwidgets
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QBrush, QColor, QCloseEvent, QDesktopServices, QDragEnterEvent, QDropEvent, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QSplitter,
    QStackedWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CheckBox,
    ComboBox,
    FluentIcon as FIF,
    FluentWindow,
    InfoBar,
    InfoBarPosition,
    LineEdit,
    NavigationItemPosition,
    PlainTextEdit,
    PrimaryPushButton,
    ProgressBar,
    PushButton,
    ScrollArea,
    SegmentedWidget,
    StrongBodyLabel,
    SubtitleLabel,
    TableWidget,
    Theme,
    TitleLabel,
    setTheme,
    setThemeColor,
)

from ..download_support import build_idle_download_status_text
from ..infrastructure.importers import cleanup_stale_import_workspaces
from ..shared import (
    APP_TITLE,
    DOWNLOAD_SOURCE_DOMESTIC,
    DOWNLOAD_SOURCE_LABELS,
    DOWNLOAD_SOURCE_OPTIONS,
    DOWNLOAD_SOURCE_SMART,
    ModTaskOptions,
    ReviewItem,
    ServerTaskOptions,
    TaskStage,
    VersionCandidate,
    get_category_label,
)
from ..tasks import run_mod_task, run_server_task
from .qt_dialogs import ChecklistDialog, VersionSelectionDialog


PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_ICON_PATH = PROJECT_ROOT / "自动筛选模组分类器.ico"

BG_COLOR = "#0F172A"
SURFACE_COLOR = "#1B2336"
SURFACE_ALT_COLOR = "#111827"
BORDER_COLOR = "#334155"
TEXT_COLOR = "#F8FAFC"
MUTED_TEXT_COLOR = "#94A3B8"
ACCENT_COLOR = "#22C55E"
WARNING_COLOR = "#F59E0B"
ERROR_COLOR = "#EF4444"


@dataclass
class HomeWidgets:
    mod_status_label: StrongBodyLabel
    mod_output_label: BodyLabel
    server_status_label: StrongBodyLabel
    server_output_label: BodyLabel


@dataclass
class ReportSectionState:
    status_label: StrongBodyLabel
    summary_edit: PlainTextEdit
    result_button: PushButton
    extra_button: Optional[PushButton]
    result_dir: Optional[Path] = None
    extra_dir: Optional[Path] = None


@dataclass
class TaskPanelState:
    stage_label: StrongBodyLabel
    status_label: BodyLabel
    progress_bar: ProgressBar
    download_label: BodyLabel
    output_label: BodyLabel
    summary_edit: PlainTextEdit
    log_edit: PlainTextEdit
    start_button: PrimaryPushButton
    result_button: PushButton
    extra_button: Optional[PushButton]
    metric_cards: Dict[str, "MetricCard"] = field(default_factory=dict)
    stage_board: Optional["StageBoard"] = None
    result_table: Optional[TableWidget] = None
    result_hint_label: Optional[BodyLabel] = None
    result_dir: Optional[Path] = None
    extra_dir: Optional[Path] = None


class ScrollablePage(ScrollArea):
    """统一页面壳子，负责滚动和头部标题。"""

    def __init__(self, page_key: str, title: str, subtitle: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.page_key = page_key
        self.setObjectName(page_key)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

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
        subtitle_label = SubtitleLabel(subtitle, header)
        subtitle_label.setWordWrap(True)
        title_label.setStyleSheet(f"color: {TEXT_COLOR};")
        subtitle_label.setStyleSheet(f"color: {MUTED_TEXT_COLOR};")
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        layout.addWidget(header)


class MetricCard(QFrame):
    """紧凑数字卡片，只展示一个重点指标。"""

    def __init__(self, title: str, value: str, note: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("metricCard")
        self.setStyleSheet(
            f"""
            QWidget#metricCard {{
                background-color: {SURFACE_ALT_COLOR};
                border: 1px solid {BORDER_COLOR};
                border-radius: 8px;
            }}
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)

        caption = BodyLabel(title, self)
        caption.setWordWrap(True)
        caption.setStyleSheet(f"color: {MUTED_TEXT_COLOR};")
        layout.addWidget(caption)

        self.value_label = TitleLabel(value, self)
        self.value_label.setStyleSheet(f"color: {TEXT_COLOR};")
        layout.addWidget(self.value_label)

        self.note_label = BodyLabel(note, self)
        self.note_label.setWordWrap(True)
        self.note_label.setStyleSheet(f"color: {MUTED_TEXT_COLOR};")
        layout.addWidget(self.note_label)

        layout.addStretch(1)

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)

    def set_note(self, note: str) -> None:
        self.note_label.setText(note)


class StageBoard(QFrame):
    """阶段时间线，跟随真实状态和日志推进。"""

    def __init__(self, title: str, stages: List[tuple[str, str]], parent: Optional[QWidget] = None):
        super().__init__(parent)
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
        self.stage_order = [key for key, _ in stages]
        self.stage_rows: Dict[str, Dict[str, QLabel]] = {}
        self.stage_details: Dict[str, str] = {}
        self.current_stage_key: Optional[str] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title_label = StrongBodyLabel(title, self)
        title_label.setStyleSheet(f"color: {TEXT_COLOR};")
        layout.addWidget(title_label)

        for stage_key, stage_title in stages:
            row = QWidget(self)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
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
        dot = row["dot"]
        title = row["title"]
        detail_label = row["detail"]

        if state == "running":
            dot_color = ACCENT_COLOR
            title_color = TEXT_COLOR
            detail_color = TEXT_COLOR
        elif state == "done":
            dot_color = ACCENT_COLOR
            title_color = TEXT_COLOR
            detail_color = MUTED_TEXT_COLOR
        elif state == "error":
            dot_color = ERROR_COLOR
            title_color = TEXT_COLOR
            detail_color = ERROR_COLOR
        else:
            dot_color = BORDER_COLOR
            title_color = MUTED_TEXT_COLOR
            detail_color = MUTED_TEXT_COLOR

        dot.setStyleSheet(f"color: {dot_color}; font-size: 14px;")
        title.setStyleSheet(f"color: {title_color}; font-size: 13px; font-weight: 600;")
        detail_label.setStyleSheet(f"color: {detail_color}; font-size: 12px;")
        detail_label.setText(detail)


class App(FluentWindow):
    def __init__(self):
        super().__init__()
        self.worker_thread: Optional[threading.Thread] = None
        self.ui_queue: "queue.Queue[dict[str, Any]]" = queue.Queue()
        self._runtime_ref: Any = None

        self.home_widgets: Optional[HomeWidgets] = None
        self.report_sections: Dict[str, ReportSectionState] = {}
        self.mod_panel: Optional[TaskPanelState] = None
        self.server_panel: Optional[TaskPanelState] = None

        cleanup_stale_import_workspaces()

        self._build_window()
        self._build_pages()
        self._refresh_home_overview()
        self._refresh_report_sections()

        self.queue_timer = QTimer(self)
        self.queue_timer.timeout.connect(self.poll_queue)
        self.queue_timer.start(120)

    def _build_window(self) -> None:
        self.setWindowTitle(APP_TITLE)
        self.resize(1380, 920)
        self.setMinimumSize(1180, 760)
        self.setAcceptDrops(True)
        self.setMicaEffectEnabled(False)
        if APP_ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(APP_ICON_PATH)))
        self.setStyleSheet(
            f"""
            QLabel {{
                color: {TEXT_COLOR};
                background: transparent;
            }}
            QCheckBox {{
                color: {TEXT_COLOR};
                background: transparent;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
            }}
            QHeaderView::section {{
                background-color: {SURFACE_ALT_COLOR};
                color: {TEXT_COLOR};
                border: 0;
                border-bottom: 1px solid {BORDER_COLOR};
                padding: 8px 10px;
            }}
            QTableCornerButton::section {{
                background-color: {SURFACE_ALT_COLOR};
                border: 0;
                border-right: 1px solid {BORDER_COLOR};
                border-bottom: 1px solid {BORDER_COLOR};
            }}
            """
        )

    def _build_pages(self) -> None:
        self.home_page = self._build_home_page()
        self.mod_page = self._build_mod_page()
        self.server_page = self._build_server_page()
        self.report_page = self._build_report_page()
        self.settings_page = self._build_settings_page()

        self.addSubInterface(self.home_page, FIF.HOME, "工作台")
        self.addSubInterface(self.mod_page, FIF.ZIP_FOLDER, "模组筛选")
        self.addSubInterface(self.server_page, FIF.COMMAND_PROMPT, "一键开服")
        self.addSubInterface(self.report_page, FIF.DOCUMENT, "结果报告")
        self.addSubInterface(
            self.settings_page,
            FIF.SETTING,
            "设置",
            position=NavigationItemPosition.BOTTOM,
        )
        self.switchTo(self.home_page)

    def _create_card(self, title: str, description: str = "") -> tuple[QFrame, QVBoxLayout]:
        card = QFrame(self)
        self._apply_card_style(card)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        title_label = StrongBodyLabel(title, card)
        title_label.setStyleSheet(f"color: {TEXT_COLOR};")
        layout.addWidget(title_label)

        if description:
            desc_label = BodyLabel(description, card)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet(f"color: {MUTED_TEXT_COLOR};")
            layout.addWidget(desc_label)

        return card, layout

    def _apply_card_style(self, widget: QWidget, variant: str = "panel") -> None:
        if variant == "metric":
            background = SURFACE_ALT_COLOR
            object_name = "metricCard"
        else:
            background = SURFACE_COLOR
            object_name = "panelCard"
        widget.setObjectName(object_name)
        widget.setStyleSheet(
            f"""
            QWidget#{object_name} {{
                background-color: {background};
                border: 1px solid {BORDER_COLOR};
                border-radius: 8px;
            }}
            """
        )

    def _apply_read_only_editor_style(self, editor: PlainTextEdit, *, console: bool = False) -> None:
        background = "#0B1220" if console else SURFACE_ALT_COLOR
        editor.setStyleSheet(
            f"""
            background-color: {background};
            color: {TEXT_COLOR};
            border: 1px solid {BORDER_COLOR};
            border-radius: 8px;
            selection-background-color: {ACCENT_COLOR};
            """
        )

    def _apply_input_style(self, widget: QWidget) -> None:
        widget.setStyleSheet(
            f"""
            background-color: {SURFACE_ALT_COLOR};
            color: {TEXT_COLOR};
            border: 1px solid {BORDER_COLOR};
            border-radius: 8px;
            padding: 0 12px;
            """
        )

    def _apply_label_tone(self, label: QLabel | BodyLabel | StrongBodyLabel, *, muted: bool = False) -> None:
        color = MUTED_TEXT_COLOR if muted else TEXT_COLOR
        label.setStyleSheet(f"color: {color};")

    def _build_tab_host(self, parent: QWidget, tabs: List[tuple[str, str, QWidget]]) -> tuple[QWidget, SegmentedWidget, QStackedWidget]:
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

    def _build_result_table(self, parent: QWidget) -> TableWidget:
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

    def _build_download_source_combo(self) -> ComboBox:
        combo = ComboBox(self)
        for code, label in DOWNLOAD_SOURCE_OPTIONS:
            combo.addItem(label, userData=code)
            if code == DOWNLOAD_SOURCE_SMART:
                combo.setCurrentIndex(combo.count() - 1)
        return combo

    def _build_home_page(self) -> ScrollablePage:
        page = ScrollablePage(
            "homePage",
            "工作台",
            "先选输入源，再决定是筛模组还是直接一键制作服务端。新界面先把主流程和日志台搭起来，后面再继续细化。",
            self,
        )

        quick_card, quick_layout = self._create_card(
            "快速开始",
            "当前版本支持目录、客户端、mrpack、CurseForge 风格 zip 直接导入，也支持把文件夹或整合包拖进窗口。",
        )
        button_row = QHBoxLayout()
        button_row.setSpacing(12)

        mod_button = PrimaryPushButton("进入模组筛选", quick_card)
        mod_button.clicked.connect(lambda: self.switchTo(self.mod_page))
        button_row.addWidget(mod_button)

        server_button = PushButton("进入一键开服", quick_card)
        server_button.clicked.connect(lambda: self.switchTo(self.server_page))
        button_row.addWidget(server_button)

        report_button = PushButton("查看结果报告", quick_card)
        report_button.clicked.connect(lambda: self.switchTo(self.report_page))
        button_row.addWidget(report_button)
        button_row.addStretch(1)
        quick_layout.addLayout(button_row)

        overview_card, overview_layout = self._create_card(
            "当前状态",
            "这里会同步两条主流程的最近状态，方便你不开页面切换也能知道任务跑到哪里了。",
        )
        mod_status_label = StrongBodyLabel("模组筛选：待运行", overview_card)
        mod_output_label = BodyLabel("最近输出：尚无结果", overview_card)
        mod_output_label.setWordWrap(True)
        server_status_label = StrongBodyLabel("一键开服：待运行", overview_card)
        server_output_label = BodyLabel("最近输出：尚无结果", overview_card)
        server_output_label.setWordWrap(True)

        overview_layout.addWidget(mod_status_label)
        overview_layout.addWidget(mod_output_label)
        overview_layout.addSpacing(8)
        overview_layout.addWidget(server_status_label)
        overview_layout.addWidget(server_output_label)
        self.home_widgets = HomeWidgets(
            mod_status_label=mod_status_label,
            mod_output_label=mod_output_label,
            server_status_label=server_status_label,
            server_output_label=server_output_label,
        )

        capability_card, capability_layout = self._create_card(
            "这一版界面重点",
            "样式先走深色 Fluent 工具台，优先把运行状态、下载状态、日志和结果目录摆清楚。",
        )
        for text in [
            "支持把目录、zip、mrpack 直接拖到窗口里。",
            "模组筛选和一键开服共用同一套后端任务入口，不重复写业务逻辑。",
            "下载状态会直接显示当前网速、线程数和完成数。",
            "版本选择、人工复核这些阻塞交互，已经单独拆成 Qt 弹窗。",
        ]:
            label = BodyLabel(f"• {text}", capability_card)
            label.setWordWrap(True)
            capability_layout.addWidget(label)

        page.container_layout.addWidget(quick_card)
        page.container_layout.addWidget(overview_card)
        page.container_layout.addWidget(capability_card)
        page.container_layout.addStretch(1)
        return page

    def _build_mod_page(self) -> ScrollablePage:
        page = ScrollablePage(
            "modPage",
            "模组筛选",
            "输入目录或整合包后，左侧负责参数和操作，右侧专门盯运行状态、阶段推进、结果预览和日志。",
            self,
        )
        workspace = QSplitter(Qt.Horizontal, page)
        workspace.setChildrenCollapsible(False)
        workspace.setHandleWidth(1)
        workspace.setStyleSheet(f"QSplitter::handle {{ background: {BG_COLOR}; }}")

        left_column = QWidget(workspace)
        left_column.setMinimumWidth(360)
        left_column.setMaximumWidth(420)
        left_layout = QVBoxLayout(left_column)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(16)

        source_card, source_layout = self._create_card("输入源", "支持目录、mrpack、zip，也支持直接拖入窗口。")
        self.mod_path_edit = LineEdit(source_card)
        self.mod_path_edit.setPlaceholderText("选择 mods 目录、客户端目录或整合包")
        self.mod_path_edit.setClearButtonEnabled(True)
        self._apply_input_style(self.mod_path_edit)
        source_layout.addWidget(self.mod_path_edit)

        source_button_row = QHBoxLayout()
        source_button_row.setSpacing(10)
        mod_folder_button = PushButton("浏览目录", source_card)
        mod_folder_button.clicked.connect(self.choose_mod_folder)
        source_button_row.addWidget(mod_folder_button)

        mod_archive_button = PushButton("选择整合包", source_card)
        mod_archive_button.clicked.connect(self.choose_mod_archive)
        source_button_row.addWidget(mod_archive_button)
        source_layout.addLayout(source_button_row)

        options_card, options_layout = self._create_card(
            "筛选策略",
            "默认先走本地元数据判断，不够再补查远程来源。智能优选会在 MCIM、BMCLAPI、官方源之间自动挑路线。",
        )
        download_title = StrongBodyLabel("下载源", options_card)
        download_title.setStyleSheet(f"color: {TEXT_COLOR};")
        options_layout.addWidget(download_title)

        self.mod_download_source_combo = self._build_download_source_combo()
        self._apply_input_style(self.mod_download_source_combo)
        options_layout.addWidget(self.mod_download_source_combo)

        self.mod_dry_run_checkbox = CheckBox("仅试运行，不移动模组", options_card)
        self.mod_use_mcmod_checkbox = CheckBox("启用 MC百科（可能需要人工验证码）", options_card)
        self.mod_use_mcmod_checkbox.setChecked(True)
        self.mod_use_cf_checkbox = CheckBox("启用 CurseForge（测试版）", options_card)
        self.mod_second_pass_checkbox = CheckBox("启用 2 次筛选补查", options_card)
        for checkbox in (
            self.mod_dry_run_checkbox,
            self.mod_use_mcmod_checkbox,
            self.mod_use_cf_checkbox,
            self.mod_second_pass_checkbox,
        ):
            options_layout.addWidget(checkbox)

        mod_start_button = PrimaryPushButton("开始筛选", options_card)
        mod_start_button.clicked.connect(self.start_mod_task)
        options_layout.addWidget(mod_start_button)

        quick_tip_card, quick_tip_layout = self._create_card(
            "输入提示",
            "拖进来的是整合包时，后端会先整理成本地工作区，再进入同一套筛选流程。",
        )
        for tip in [
            "目录、zip、mrpack 都支持直接拖入当前窗口。",
            "如果只想先看判定结果，可以勾选“仅试运行”。",
            "待确认数量多的时候，优先看结果预览表和报告页。",
        ]:
            label = BodyLabel(f"• {tip}", quick_tip_card)
            label.setWordWrap(True)
            self._apply_label_tone(label, muted=True)
            quick_tip_layout.addWidget(label)

        left_layout.addWidget(source_card)
        left_layout.addWidget(options_card)
        left_layout.addWidget(quick_tip_card)
        left_layout.addStretch(1)

        right_column = QWidget(workspace)
        right_layout = QVBoxLayout(right_column)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(16)

        top_row = QHBoxLayout()
        top_row.setSpacing(16)

        status_card, status_layout = self._create_card("运行状态", "核心状态放这里，不需要盯着整页滚动。")
        mod_stage_label = StrongBodyLabel("当前阶段：等待开始", status_card)
        mod_stage_label.setStyleSheet(f"color: {TEXT_COLOR};")
        status_layout.addWidget(mod_stage_label)

        mod_status_label = BodyLabel("请选择输入源，然后开始筛选。", status_card)
        mod_status_label.setWordWrap(True)
        self._apply_label_tone(mod_status_label, muted=True)
        status_layout.addWidget(mod_status_label)

        mod_progress_bar = ProgressBar(status_card)
        mod_progress_bar.setRange(0, 100)
        mod_progress_bar.setValue(0)
        status_layout.addWidget(mod_progress_bar)

        mod_download_label = BodyLabel(build_idle_download_status_text(), status_card)
        mod_download_label.setWordWrap(True)
        self._apply_label_tone(mod_download_label, muted=True)
        status_layout.addWidget(mod_download_label)

        mod_output_label = BodyLabel("输出位置：尚未运行", status_card)
        mod_output_label.setWordWrap(True)
        mod_output_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._apply_label_tone(mod_output_label, muted=True)
        status_layout.addWidget(mod_output_label)

        mod_action_row = QHBoxLayout()
        mod_result_button = PushButton("打开结果目录", status_card)
        mod_result_button.setEnabled(False)
        mod_result_button.clicked.connect(lambda: self.open_panel_path("mod", "result"))
        mod_action_row.addWidget(mod_result_button)
        mod_report_button = PushButton("查看结果报告", status_card)
        mod_report_button.clicked.connect(lambda: self.switchTo(self.report_page))
        mod_action_row.addWidget(mod_report_button)
        mod_action_row.addStretch(1)
        status_layout.addLayout(mod_action_row)

        mod_stage_board = StageBoard(
            "任务阶段",
            [
                ("scan", "读取目录"),
                ("classify", "首轮筛选"),
                ("second-pass", "二次筛选"),
                ("organize", "整理结果"),
                ("report", "写出报告"),
                ("complete", "完成"),
            ],
            right_column,
        )

        top_row.addWidget(status_card, 3)
        top_row.addWidget(mod_stage_board, 2)
        right_layout.addLayout(top_row)

        metric_row = QHBoxLayout()
        metric_row.setSpacing(12)
        mod_keep_card = MetricCard("服务端保留", "--", "能直接留在服务端的模组")
        mod_client_card = MetricCard("纯客户端", "--", "可以自动移出服务端的模组")
        mod_unknown_card = MetricCard("待确认", "--", "这一批建议你人工再看一眼")
        metric_row.addWidget(mod_keep_card)
        metric_row.addWidget(mod_client_card)
        metric_row.addWidget(mod_unknown_card)
        right_layout.addLayout(metric_row)

        preview_card, preview_layout = self._create_card("结果与控制台", "筛选完成后，结果预览会直接从分类报告里读取重点条目。")
        result_page = QWidget(preview_card)
        result_layout = QVBoxLayout(result_page)
        result_layout.setContentsMargins(0, 0, 0, 0)
        result_layout.setSpacing(10)

        mod_result_hint_label = BodyLabel("还没有筛选结果。任务完成后，这里会优先展示待确认和关键条目。", result_page)
        mod_result_hint_label.setWordWrap(True)
        self._apply_label_tone(mod_result_hint_label, muted=True)
        result_layout.addWidget(mod_result_hint_label)

        mod_result_table = self._build_result_table(result_page)
        result_layout.addWidget(mod_result_table)

        summary_page = QWidget(preview_card)
        summary_layout = QVBoxLayout(summary_page)
        summary_layout.setContentsMargins(0, 0, 0, 0)
        mod_summary_edit = PlainTextEdit(summary_page)
        mod_summary_edit.setReadOnly(True)
        mod_summary_edit.setPlainText("任务完成后，这里会展示结果摘要、输出目录和报告路径。")
        self._apply_read_only_editor_style(mod_summary_edit)
        summary_layout.addWidget(mod_summary_edit)

        log_page = QWidget(preview_card)
        log_layout = QVBoxLayout(log_page)
        log_layout.setContentsMargins(0, 0, 0, 0)
        mod_log_edit = PlainTextEdit(log_page)
        mod_log_edit.setReadOnly(True)
        mod_log_edit.setPlainText("实时日志会滚动显示在这里。")
        self._apply_read_only_editor_style(mod_log_edit, console=True)
        log_layout.addWidget(mod_log_edit)

        tab_host, _, _ = self._build_tab_host(
            preview_card,
            [
                ("results", "结果预览", result_page),
                ("summary", "任务摘要", summary_page),
                ("logs", "实时日志", log_page),
            ],
        )
        preview_layout.addWidget(tab_host)
        right_layout.addWidget(preview_card, 1)

        workspace.addWidget(left_column)
        workspace.addWidget(right_column)
        workspace.setStretchFactor(0, 0)
        workspace.setStretchFactor(1, 1)
        page.container_layout.addWidget(workspace, 1)

        self.mod_panel = TaskPanelState(
            stage_label=mod_stage_label,
            status_label=mod_status_label,
            progress_bar=mod_progress_bar,
            download_label=mod_download_label,
            output_label=mod_output_label,
            summary_edit=mod_summary_edit,
            log_edit=mod_log_edit,
            start_button=mod_start_button,
            result_button=mod_result_button,
            extra_button=None,
            metric_cards={
                "server-keep": mod_keep_card,
                "client-only": mod_client_card,
                "unknown": mod_unknown_card,
            },
            stage_board=mod_stage_board,
            result_table=mod_result_table,
            result_hint_label=mod_result_hint_label,
        )
        return page

    def _build_server_page(self) -> ScrollablePage:
        page = ScrollablePage(
            "serverPage",
            "一键开服",
            "左侧准备输入和参数，右侧专门盯版本识别、安装阶段、启动验证和完整日志。",
            self,
        )
        workspace = QSplitter(Qt.Horizontal, page)
        workspace.setChildrenCollapsible(False)
        workspace.setHandleWidth(1)
        workspace.setStyleSheet(f"QSplitter::handle {{ background: {BG_COLOR}; }}")

        left_column = QWidget(workspace)
        left_column.setMinimumWidth(360)
        left_column.setMaximumWidth(420)
        left_layout = QVBoxLayout(left_column)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(16)

        source_card, source_layout = self._create_card("客户端输入源", "支持完整客户端目录、mrpack、CurseForge 风格 zip。")
        self.server_client_path_edit = LineEdit(source_card)
        self.server_client_path_edit.setPlaceholderText("选择客户端目录或整合包")
        self.server_client_path_edit.setClearButtonEnabled(True)
        self._apply_input_style(self.server_client_path_edit)
        source_layout.addWidget(self.server_client_path_edit)

        source_button_row = QHBoxLayout()
        source_button_row.setSpacing(10)
        client_folder_button = PushButton("浏览目录", source_card)
        client_folder_button.clicked.connect(self.choose_client_folder)
        source_button_row.addWidget(client_folder_button)

        client_archive_button = PushButton("选择整合包", source_card)
        client_archive_button.clicked.connect(self.choose_server_archive)
        source_button_row.addWidget(client_archive_button)
        source_layout.addLayout(source_button_row)

        output_card, output_layout = self._create_card("服务端输出目录", "建议先新建一个空目录，避免和现有文件混在一起。")
        self.server_output_path_edit = LineEdit(output_card)
        self.server_output_path_edit.setPlaceholderText("选择新的空服务端输出目录")
        self.server_output_path_edit.setClearButtonEnabled(True)
        self._apply_input_style(self.server_output_path_edit)
        output_layout.addWidget(self.server_output_path_edit)

        output_button = PushButton("浏览输出目录", output_card)
        output_button.clicked.connect(self.choose_output_folder)
        output_layout.addWidget(output_button)

        options_card, options_layout = self._create_card(
            "开服策略",
            "整合包会先被整理成本地客户端工作区，再走版本识别、安装器下载、服务端安装、模组筛选和两次启动验证。",
        )
        download_title = StrongBodyLabel("下载源", options_card)
        download_title.setStyleSheet(f"color: {TEXT_COLOR};")
        options_layout.addWidget(download_title)

        self.server_download_source_combo = self._build_download_source_combo()
        self._apply_input_style(self.server_download_source_combo)
        options_layout.addWidget(self.server_download_source_combo)

        self.server_use_mcmod_checkbox = CheckBox("启用 MC百科（可能需要人工验证码）", options_card)
        self.server_use_mcmod_checkbox.setChecked(True)
        self.server_use_cf_checkbox = CheckBox("启用 CurseForge（测试版）", options_card)
        self.server_second_pass_checkbox = CheckBox("启用 2 次筛选补查", options_card)
        for checkbox in (
            self.server_use_mcmod_checkbox,
            self.server_use_cf_checkbox,
            self.server_second_pass_checkbox,
        ):
            options_layout.addWidget(checkbox)

        server_start_button = PrimaryPushButton("开始制作服务端", options_card)
        server_start_button.clicked.connect(self.start_server_task)
        options_layout.addWidget(server_start_button)

        quick_tip_card, quick_tip_layout = self._create_card(
            "执行提示",
            "一键开服过程中如果遇到版本选择或复制核查，会直接弹出阻塞弹窗，不会静默跳过。",
        )
        for tip in [
            "输出目录必须是新的空目录。",
            "开服流程会自动下载缺失环境和安装器。",
            "首次启动、写入 eula、二次启动验证的结果都能在右侧时间线里看到。",
        ]:
            label = BodyLabel(f"• {tip}", quick_tip_card)
            label.setWordWrap(True)
            self._apply_label_tone(label, muted=True)
            quick_tip_layout.addWidget(label)

        left_layout.addWidget(source_card)
        left_layout.addWidget(output_card)
        left_layout.addWidget(options_card)
        left_layout.addWidget(quick_tip_card)
        left_layout.addStretch(1)

        right_column = QWidget(workspace)
        right_layout = QVBoxLayout(right_column)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(16)

        top_row = QHBoxLayout()
        top_row.setSpacing(16)

        status_card, status_layout = self._create_card("运行状态", "把当前阶段、下载状态、输出路径和快捷操作集中放到一起。")
        server_stage_label = StrongBodyLabel("当前阶段：等待开始", status_card)
        server_stage_label.setStyleSheet(f"color: {TEXT_COLOR};")
        status_layout.addWidget(server_stage_label)

        server_status_label = BodyLabel("请选择客户端输入源和输出目录，然后开始制作服务端。", status_card)
        server_status_label.setWordWrap(True)
        self._apply_label_tone(server_status_label, muted=True)
        status_layout.addWidget(server_status_label)

        server_progress_bar = ProgressBar(status_card)
        server_progress_bar.setRange(0, 100)
        server_progress_bar.setValue(0)
        status_layout.addWidget(server_progress_bar)

        server_download_label = BodyLabel(build_idle_download_status_text(), status_card)
        server_download_label.setWordWrap(True)
        self._apply_label_tone(server_download_label, muted=True)
        status_layout.addWidget(server_download_label)

        server_output_label = BodyLabel("输出位置：尚未运行", status_card)
        server_output_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        server_output_label.setWordWrap(True)
        self._apply_label_tone(server_output_label, muted=True)
        status_layout.addWidget(server_output_label)

        server_action_row = QHBoxLayout()
        server_result_button = PushButton("打开服务端目录", status_card)
        server_result_button.setEnabled(False)
        server_result_button.clicked.connect(lambda: self.open_panel_path("server", "result"))
        server_action_row.addWidget(server_result_button)

        server_extra_button = PushButton("打开日志目录", status_card)
        server_extra_button.setEnabled(False)
        server_extra_button.clicked.connect(lambda: self.open_panel_path("server", "extra"))
        server_action_row.addWidget(server_extra_button)

        server_report_button = PushButton("查看结果报告", status_card)
        server_report_button.clicked.connect(lambda: self.switchTo(self.report_page))
        server_action_row.addWidget(server_report_button)
        server_action_row.addStretch(1)
        status_layout.addLayout(server_action_row)

        server_stage_board = StageBoard(
            "开服阶段",
            [
                ("scan", "识别客户端"),
                ("precheck", "匹配 Java"),
                ("installer", "下载安装器"),
                ("install", "安装服务端"),
                ("classify", "筛选模组"),
                ("copy-mods", "复制模组"),
                ("copy-configs", "复制配置"),
                ("first-boot", "首次启动"),
                ("patch", "修正配置"),
                ("verify", "二次验证"),
                ("complete", "完成"),
            ],
            right_column,
        )

        top_row.addWidget(status_card, 3)
        top_row.addWidget(server_stage_board, 2)
        right_layout.addLayout(top_row)

        preview_card, preview_layout = self._create_card("摘要与日志", "安装过程里最重要的两块信息都固定在这里，不再来回翻页。")
        summary_page = QWidget(preview_card)
        summary_layout = QVBoxLayout(summary_page)
        summary_layout.setContentsMargins(0, 0, 0, 0)
        server_summary_edit = PlainTextEdit(summary_page)
        server_summary_edit.setReadOnly(True)
        server_summary_edit.setPlainText("任务完成后，这里会展示服务端目录、日志目录和启动脚本路径。")
        self._apply_read_only_editor_style(server_summary_edit)
        summary_layout.addWidget(server_summary_edit)

        log_page = QWidget(preview_card)
        log_layout = QVBoxLayout(log_page)
        log_layout.setContentsMargins(0, 0, 0, 0)
        server_log_edit = PlainTextEdit(log_page)
        server_log_edit.setReadOnly(True)
        server_log_edit.setPlainText("实时日志会滚动显示在这里。")
        self._apply_read_only_editor_style(server_log_edit, console=True)
        log_layout.addWidget(server_log_edit)

        tab_host, _, _ = self._build_tab_host(
            preview_card,
            [
                ("summary", "任务摘要", summary_page),
                ("logs", "实时日志", log_page),
            ],
        )
        preview_layout.addWidget(tab_host)
        right_layout.addWidget(preview_card, 1)

        workspace.addWidget(left_column)
        workspace.addWidget(right_column)
        workspace.setStretchFactor(0, 0)
        workspace.setStretchFactor(1, 1)
        page.container_layout.addWidget(workspace, 1)

        self.server_panel = TaskPanelState(
            stage_label=server_stage_label,
            status_label=server_status_label,
            progress_bar=server_progress_bar,
            download_label=server_download_label,
            output_label=server_output_label,
            summary_edit=server_summary_edit,
            log_edit=server_log_edit,
            start_button=server_start_button,
            result_button=server_result_button,
            extra_button=server_extra_button,
            stage_board=server_stage_board,
        )
        return page

    def _build_report_page(self) -> ScrollablePage:
        page = ScrollablePage(
            "reportPage",
            "结果报告",
            "把最近一次模组筛选和最近一次一键开服的摘要集中放这里，方便直接打开结果目录或日志目录。",
            self,
        )

        mod_card, mod_layout = self._create_card("模组筛选结果")
        mod_status = StrongBodyLabel("当前还没有模组筛选结果。", mod_card)
        mod_layout.addWidget(mod_status)
        mod_summary = PlainTextEdit(mod_card)
        mod_summary.setReadOnly(True)
        mod_summary.setMinimumHeight(180)
        mod_summary.setPlainText("完成一次模组筛选后，这里会同步结果摘要。")
        self._apply_read_only_editor_style(mod_summary)
        mod_layout.addWidget(mod_summary)

        mod_button_row = QHBoxLayout()
        mod_result_button = PushButton("打开结果目录", mod_card)
        mod_result_button.setEnabled(False)
        mod_result_button.clicked.connect(lambda: self._open_report_path("mod", "result"))
        mod_button_row.addWidget(mod_result_button)
        mod_button_row.addStretch(1)
        mod_layout.addLayout(mod_button_row)

        server_card, server_layout = self._create_card("一键开服结果")
        server_status = StrongBodyLabel("当前还没有服务端制作结果。", server_card)
        server_layout.addWidget(server_status)
        server_summary = PlainTextEdit(server_card)
        server_summary.setReadOnly(True)
        server_summary.setMinimumHeight(180)
        server_summary.setPlainText("完成一次服务端制作后，这里会同步服务端目录、日志目录和启动脚本位置。")
        self._apply_read_only_editor_style(server_summary)
        server_layout.addWidget(server_summary)

        server_button_row = QHBoxLayout()
        server_result_button = PushButton("打开服务端目录", server_card)
        server_result_button.setEnabled(False)
        server_result_button.clicked.connect(lambda: self._open_report_path("server", "result"))
        server_button_row.addWidget(server_result_button)

        server_extra_button = PushButton("打开日志目录", server_card)
        server_extra_button.setEnabled(False)
        server_extra_button.clicked.connect(lambda: self._open_report_path("server", "extra"))
        server_button_row.addWidget(server_extra_button)
        server_button_row.addStretch(1)
        server_layout.addLayout(server_button_row)

        page.container_layout.addWidget(mod_card)
        page.container_layout.addWidget(server_card)
        page.container_layout.addStretch(1)

        self.report_sections["mod"] = ReportSectionState(
            status_label=mod_status,
            summary_edit=mod_summary,
            result_button=mod_result_button,
            extra_button=None,
        )
        self.report_sections["server"] = ReportSectionState(
            status_label=server_status,
            summary_edit=server_summary,
            result_button=server_result_button,
            extra_button=server_extra_button,
        )
        return page

    def _build_settings_page(self) -> ScrollablePage:
        page = ScrollablePage(
            "settingsPage",
            "设置",
            "这一页先放技术栈、设计方向和缓存清理入口，后面再把更细的偏好配置补进来。",
            self,
        )

        stack_card, stack_layout = self._create_card("当前界面技术栈")
        for text in [
            f"桌面框架：PySide6 {getattr(sys.modules.get('PySide6'), '__version__', '')}".strip(),
            f"Fluent 组件：qfluentwidgets {qfluentwidgets.__version__}",
            "设计方向：深色 Fluent 工具台，优先突出运行状态、下载状态、日志和结果目录。",
        ]:
            label = BodyLabel(text, stack_card)
            label.setWordWrap(True)
            stack_layout.addWidget(label)

        support_card, support_layout = self._create_card("输入与缓存")
        for text in [
            "支持目录、mrpack、zip 直接导入。",
            "支持拖放文件夹和整合包到窗口中。",
            "整合包缓存和浏览器缓存会在启动与退出时做一次清理。",
        ]:
            label = BodyLabel(f"• {text}", support_card)
            label.setWordWrap(True)
            support_layout.addWidget(label)

        cleanup_button = PrimaryPushButton("立即清理整合包缓存", support_card)
        cleanup_button.clicked.connect(self.cleanup_import_cache)
        support_layout.addWidget(cleanup_button, 0, Qt.AlignLeft)

        page.container_layout.addWidget(stack_card)
        page.container_layout.addWidget(support_card)
        page.container_layout.addStretch(1)
        return page

    def choose_mod_folder(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "选择 mods 目录")
        if selected:
            self.mod_path_edit.setText(selected)

    def choose_mod_archive(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "选择整合包文件",
            "",
            "整合包 (*.mrpack *.zip);;MRPACK (*.mrpack);;ZIP (*.zip);;所有文件 (*.*)",
        )
        if selected:
            self.mod_path_edit.setText(selected)

    def choose_client_folder(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "选择客户端实例目录")
        if selected:
            self.server_client_path_edit.setText(selected)

    def choose_server_archive(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "选择整合包文件",
            "",
            "整合包 (*.mrpack *.zip);;MRPACK (*.mrpack);;ZIP (*.zip);;所有文件 (*.*)",
        )
        if selected:
            self.server_client_path_edit.setText(selected)

    def choose_output_folder(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "选择新的空服务端输出目录")
        if selected:
            self.server_output_path_edit.setText(selected)

    def cleanup_import_cache(self) -> None:
        cleanup_stale_import_workspaces()
        InfoBar.success(
            "缓存已清理",
            "整合包残留缓存和临时工作区已经尝试清理。",
            duration=2500,
            position=InfoBarPosition.TOP_RIGHT,
            parent=self,
        )

    def validate_source_path(self, path: Path, target_name: str) -> bool:
        if path.is_dir():
            return True
        if path.is_file() and path.suffix.lower() in {".zip", ".mrpack"}:
            return True
        if path.is_file():
            self.show_error(f"{target_name}当前只支持目录、.zip 和 .mrpack 文件。")
            return False
        self.show_error(f"{target_name}不存在。")
        return False

    def resolve_download_source(self, combo: ComboBox) -> str:
        current = combo.currentData()
        if isinstance(current, str) and current:
            return current
        current_text = combo.currentText().strip()
        if current_text in {value for value, _ in DOWNLOAD_SOURCE_OPTIONS}:
            return current_text
        for value, label in DOWNLOAD_SOURCE_OPTIONS:
            if current_text == label:
                return value
        if current_text == DOWNLOAD_SOURCE_LABELS.get(DOWNLOAD_SOURCE_DOMESTIC):
            return DOWNLOAD_SOURCE_SMART
        return DOWNLOAD_SOURCE_SMART

    def start_mod_task(self) -> None:
        if self.worker_thread and self.worker_thread.is_alive():
            self.show_info("任务正在运行，请先等待当前任务结束。")
            return

        source_text = self.mod_path_edit.text().strip()
        if not source_text:
            self.show_warning("请先选择一个 mods 目录、客户端目录或整合包。")
            return

        source_path = Path(source_text)
        if not source_path.exists():
            self.show_error("所选目录或整合包不存在。")
            return
        if not self.validate_source_path(source_path, "模组筛选输入源"):
            return

        assert self.mod_panel is not None
        self.clear_panel("mod")
        self.mod_panel.status_label.setText("准备开始…")
        self._set_busy_state(True)
        self._refresh_home_overview(panel_key="mod", status="运行中", output=None)

        options = ModTaskOptions(
            mods_path=source_path,
            download_source=self.resolve_download_source(self.mod_download_source_combo),
            dry_run=self.mod_dry_run_checkbox.isChecked(),
            use_mcmod=self.mod_use_mcmod_checkbox.isChecked(),
            use_curseforge=self.mod_use_cf_checkbox.isChecked(),
            enable_second_pass=self.mod_second_pass_checkbox.isChecked(),
        )
        self.worker_thread = threading.Thread(
            target=run_mod_task,
            args=(
                options,
                lambda kind, payload: self.emit("mod", kind, payload),
                self.set_runtime_ref,
            ),
            daemon=True,
        )
        self.worker_thread.start()

    def start_server_task(self) -> None:
        if self.worker_thread and self.worker_thread.is_alive():
            self.show_info("任务正在运行，请先等待当前任务结束。")
            return

        source_text = self.server_client_path_edit.text().strip()
        output_text = self.server_output_path_edit.text().strip()
        if not source_text:
            self.show_warning("请先选择客户端目录或整合包。")
            return
        if not output_text:
            self.show_warning("请先选择服务端输出目录。")
            return

        source_path = Path(source_text)
        if not source_path.exists():
            self.show_error("所选客户端目录或整合包不存在。")
            return
        if not self.validate_source_path(source_path, "一键开服输入源"):
            return

        assert self.server_panel is not None
        self.clear_panel("server")
        self.server_panel.status_label.setText("准备开始…")
        self._set_busy_state(True)
        self._refresh_home_overview(panel_key="server", status="运行中", output=None)

        options = ServerTaskOptions(
            client_dir=source_path,
            output_dir=Path(output_text),
            download_source=self.resolve_download_source(self.server_download_source_combo),
            use_mcmod=self.server_use_mcmod_checkbox.isChecked(),
            use_curseforge=self.server_use_cf_checkbox.isChecked(),
            enable_second_pass=self.server_second_pass_checkbox.isChecked(),
        )
        self.worker_thread = threading.Thread(
            target=run_server_task,
            args=(
                options,
                lambda kind, payload: self.emit("server", kind, payload),
                self.set_runtime_ref,
                self.request_version_choice,
                self.request_checklist,
            ),
            daemon=True,
        )
        self.worker_thread.start()

    def _set_busy_state(self, running: bool) -> None:
        for panel in (self.mod_panel, self.server_panel):
            if panel is not None:
                panel.start_button.setEnabled(not running)

    def clear_panel(self, panel_key: str) -> None:
        panel = self.get_panel(panel_key)
        panel.log_edit.clear()
        panel.summary_edit.setPlainText("任务进行中，完成后这里会刷新摘要。")
        panel.progress_bar.setValue(0)
        panel.output_label.setText("输出位置：运行中")
        panel.download_label.setText(build_idle_download_status_text())
        panel.stage_label.setText("当前阶段：准备开始")
        if panel.stage_board is not None:
            panel.stage_board.reset()
        panel.result_dir = None
        panel.extra_dir = None
        panel.result_button.setEnabled(False)
        if panel.extra_button is not None:
            panel.extra_button.setEnabled(False)
        for metric_card in panel.metric_cards.values():
            metric_card.set_value("--")
        if panel.result_table is not None:
            panel.result_table.clearContents()
            panel.result_table.setRowCount(0)
        if panel.result_hint_label is not None:
            panel.result_hint_label.setText("任务进行中，完成后会优先展示待确认和关键条目。")

    def get_panel(self, panel_key: str) -> TaskPanelState:
        if panel_key == "mod":
            assert self.mod_panel is not None
            return self.mod_panel
        assert self.server_panel is not None
        return self.server_panel

    def emit(self, panel: str, kind: str, payload: Any) -> None:
        self.ui_queue.put({"panel": panel, "kind": kind, "payload": payload})

    def append_log(self, panel_key: str, message: str) -> None:
        if not message:
            return
        panel = self.get_panel(panel_key)
        panel.log_edit.appendPlainText(message.rstrip())

    def request_version_choice(self, candidates: List[VersionCandidate]) -> Optional[VersionCandidate]:
        event = threading.Event()
        request = {"kind": "version", "candidates": candidates, "event": event, "response": None}
        self.ui_queue.put({"panel": "server", "kind": "ui-request", "payload": request})
        event.wait()
        return request["response"]

    def request_checklist(self, title: str, message: str, items: List[ReviewItem]) -> Optional[List[str]]:
        event = threading.Event()
        request = {
            "kind": "checklist",
            "title": title,
            "message": message,
            "items": items,
            "event": event,
            "response": None,
        }
        self.ui_queue.put({"panel": "server", "kind": "ui-request", "payload": request})
        event.wait()
        return request["response"]

    def poll_queue(self) -> None:
        while True:
            try:
                event = self.ui_queue.get_nowait()
            except queue.Empty:
                break

            panel_key = event["panel"]
            kind = event["kind"]
            payload = event["payload"]
            panel = self.get_panel(panel_key)

            if kind == "warning":
                self.show_warning(str(payload))
                continue

            if kind == "log":
                self.append_log(panel_key, str(payload))
                self._update_stage_by_message(panel_key, str(payload))
            elif kind == "status":
                panel.status_label.setText(str(payload))
                self._update_stage_by_message(panel_key, str(payload))
            elif kind == "progress":
                panel.progress_bar.setValue(max(0, min(100, int(float(payload)))))
            elif kind == "output":
                panel.output_label.setText(f"输出位置：{payload}")
            elif kind == "download-stats":
                panel.download_label.setText(str(payload))
            elif kind == "done":
                panel.result_dir = payload.get("result_dir")
                panel.extra_dir = payload.get("extra_dir")
                panel.status_label.setText(payload["status"])
                panel.progress_bar.setValue(100)
                panel.output_label.setText(f"输出位置：{payload['output']}")
                panel.download_label.setText(build_idle_download_status_text())
                panel.summary_edit.setPlainText(payload.get("summary", payload["status"]))
                panel.stage_label.setText("当前阶段：已完成")
                if panel.stage_board is not None:
                    panel.stage_board.finish(payload["status"])
                panel.result_button.setEnabled(bool(panel.result_dir))
                if panel.extra_button is not None:
                    panel.extra_button.setEnabled(bool(panel.extra_dir))
                self._update_panel_metrics(panel_key, payload)
                if panel_key == "mod":
                    self._load_mod_result_preview(panel.result_dir)
                self._update_report_section(panel_key, payload["status"], payload.get("summary", ""), panel.result_dir, panel.extra_dir)
                self._refresh_home_overview(panel_key=panel_key, status="已完成", output=payload.get("output"))
                self._set_busy_state(False)
                self.show_success(payload["status"])
            elif kind == "error":
                panel.status_label.setText("运行失败")
                panel.output_label.setText("输出位置：失败")
                panel.download_label.setText(build_idle_download_status_text())
                panel.summary_edit.setPlainText(str(payload))
                panel.stage_label.setText("当前阶段：运行失败")
                if panel.stage_board is not None:
                    panel.stage_board.fail(self._summarize_error_text(str(payload)))
                self.append_log(panel_key, str(payload))
                if panel.metric_cards:
                    for metric_card in panel.metric_cards.values():
                        metric_card.set_value("失败")
                self._update_report_section(panel_key, "运行失败", str(payload), panel.result_dir, panel.extra_dir)
                self._refresh_home_overview(panel_key=panel_key, status="失败", output=None)
                self._set_busy_state(False)
                self.show_error(self._summarize_error_text(str(payload)))
            elif kind == "ui-request":
                if payload["kind"] == "version":
                    dialog = VersionSelectionDialog(payload["candidates"], self)
                    dialog.exec()
                    payload["response"] = dialog.selected_candidate
                elif payload["kind"] == "checklist":
                    dialog = ChecklistDialog(payload["title"], payload["message"], payload["items"], self)
                    dialog.exec()
                    payload["response"] = dialog.selected_keys
                payload["event"].set()

    def _update_panel_metrics(self, panel_key: str, payload: Dict[str, Any]) -> None:
        if panel_key != "mod" or not self.mod_panel:
            return

        summary = payload.get("summary", "")
        mapping = {
            "server-keep": r"服务端保留:\s*(\d+)",
            "client-only": r"纯客户端移出:\s*(\d+)",
            "unknown": r"无法分类:\s*(\d+)",
        }
        for key, pattern in mapping.items():
            metric_card = self.mod_panel.metric_cards.get(key)
            if metric_card is None:
                continue
            match = re.search(pattern, summary)
            metric_card.set_value(match.group(1) if match else "--")

    def _detect_stage_key(self, panel_key: str, message: str) -> Optional[str]:
        text = str(message or "")
        if not text:
            return None

        if panel_key == "mod":
            mod_rules = [
                ("complete", ["分类完成", "写出报告"]),
                ("report", ["正在写出报告", "json 报告", "csv 报告"]),
                ("organize", ["正在整理分类结果目录", "最终结果"]),
                ("second-pass", ["2次筛选", "二次筛选"]),
                ("classify", ["正在汇总", "联网分类", "->", "开始扫描目录", "共发现"]),
                ("scan", ["开始扫描目录", "共发现", "扫描目录"]),
            ]
            for stage_key, markers in mod_rules:
                if any(marker in text for marker in markers):
                    return stage_key
            return None

        server_rules = [
            ("complete", [TaskStage.COMPLETE.value, "服务端制作完成"]),
            ("verify", [TaskStage.VERIFY_BOOT.value, "第二次启动验证"]),
            ("patch", [TaskStage.PATCH_CONFIG.value, "写入 eula", "server.properties"]),
            ("first-boot", [TaskStage.FIRST_BOOT.value, "首次启动"]),
            ("copy-configs", [TaskStage.COPY_CONFIGS.value, "复制配置目录", "收集配置目录候选"]),
            ("copy-mods", [TaskStage.COPY_MODS.value, "复制服务端模组"]),
            ("classify", [TaskStage.CLASSIFY_MODS.value, "分析客户端 mods", "mod复制核查"]),
            ("install", [TaskStage.INSTALL_SERVER.value, "安装服务端"]),
            ("installer", [TaskStage.DOWNLOAD_INSTALLER.value, "解析官方安装器地址", "下载安装器"]),
            ("precheck", [TaskStage.PRECHECK.value, "匹配 Java", "需要 Java"]),
            ("scan", [TaskStage.CLIENT_SCAN.value, "识别客户端实例根目录", "扫描版本清单", "目标版本"]),
        ]
        for stage_key, markers in server_rules:
            if any(marker in text for marker in markers):
                return stage_key
        return None

    def _update_stage_by_message(self, panel_key: str, message: str) -> None:
        panel = self.get_panel(panel_key)
        if panel.stage_board is None:
            return
        stage_key = self._detect_stage_key(panel_key, message)
        if stage_key is None:
            return
        panel.stage_board.activate(stage_key, str(message))
        stage_title = panel.stage_board.stage_rows[stage_key]["title"].text()
        panel.stage_label.setText(f"当前阶段：{stage_title}")

    def _load_mod_result_preview(self, result_dir: Optional[Path]) -> None:
        if not self.mod_panel or self.mod_panel.result_table is None:
            return

        table = self.mod_panel.result_table
        hint_label = self.mod_panel.result_hint_label
        table.clearContents()
        table.setRowCount(0)

        if not result_dir:
            if hint_label is not None:
                hint_label.setText("当前还没有可读取的结果目录。")
            return

        report_path = result_dir / "分类报告.json"
        if not report_path.exists():
            if hint_label is not None:
                hint_label.setText("筛选已经完成，但还没找到分类报告。")
            return

        try:
            rows = json.loads(report_path.read_text(encoding="utf-8"))
        except Exception as exc:
            if hint_label is not None:
                hint_label.setText(f"读取分类报告失败：{exc}")
            return

        priority = {"unknown": 0, "server-keep": 1, "client-only": 2}
        ordered_rows = sorted(rows, key=lambda row: priority.get(row.get("Category", ""), 9))
        preview_rows = ordered_rows[:40]
        table.setRowCount(len(preview_rows))

        for row_index, row in enumerate(preview_rows):
            values = [
                str(row.get("FileName", "")),
                get_category_label(str(row.get("Category", ""))),
                str(row.get("DecisionSource", "")),
                str(row.get("Reason", "")),
            ]
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                item.setForeground(QBrush(QColor(TEXT_COLOR)))
                table.setItem(row_index, column_index, item)

        if hint_label is not None:
            unknown_count = sum(1 for row in rows if row.get("Category") == "unknown")
            hint_label.setText(
                f"已读取 {len(rows)} 条分类结果，当前预览前 {len(preview_rows)} 条，其中待确认 {unknown_count} 条。"
            )

    def _update_report_section(
        self,
        panel_key: str,
        status: str,
        summary: str,
        result_dir: Optional[Path],
        extra_dir: Optional[Path],
    ) -> None:
        section = self.report_sections.get(panel_key)
        if section is None:
            return
        section.status_label.setText(status)
        section.summary_edit.setPlainText(summary or status)
        section.result_dir = result_dir
        section.extra_dir = extra_dir
        section.result_button.setEnabled(bool(result_dir))
        if section.extra_button is not None:
            section.extra_button.setEnabled(bool(extra_dir))

    def _refresh_home_overview(
        self,
        panel_key: Optional[str] = None,
        status: Optional[str] = None,
        output: Optional[str] = None,
    ) -> None:
        if self.home_widgets is None:
            return

        if panel_key == "mod":
            if status:
                self.home_widgets.mod_status_label.setText(f"模组筛选：{status}")
            if output:
                self.home_widgets.mod_output_label.setText(f"最近输出：{output}")
        elif panel_key == "server":
            if status:
                self.home_widgets.server_status_label.setText(f"一键开服：{status}")
            if output:
                self.home_widgets.server_output_label.setText(f"最近输出：{output}")

    def _refresh_report_sections(self) -> None:
        for section in self.report_sections.values():
            section.result_button.setEnabled(False)
            if section.extra_button is not None:
                section.extra_button.setEnabled(False)

    def _summarize_error_text(self, payload: str) -> str:
        lines = [line.strip() for line in payload.splitlines() if line.strip()]
        for line in reversed(lines):
            if line.startswith(("RuntimeError:", "ValueError:", "FileNotFoundError:", "Exception:")):
                return line
        return lines[-1] if lines else "运行失败，详细信息已经写入日志。"

    def show_info(self, message: str) -> None:
        QMessageBox.information(self, APP_TITLE, message)

    def show_warning(self, message: str) -> None:
        QMessageBox.warning(self, APP_TITLE, message)

    def show_error(self, message: str) -> None:
        QMessageBox.critical(self, APP_TITLE, message)

    def show_success(self, message: str) -> None:
        InfoBar.success(
            "任务完成",
            message,
            duration=3500,
            position=InfoBarPosition.TOP_RIGHT,
            parent=self,
        )

    def _open_path(self, path: Optional[Path]) -> None:
        if not path or not path.exists():
            self.show_info("当前还没有可打开的目录。")
            return
        if os.name == "nt":
            os.startfile(str(path))
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def open_panel_path(self, panel_key: str, target: str) -> None:
        panel = self.get_panel(panel_key)
        path = panel.result_dir if target == "result" else panel.extra_dir
        self._open_path(path)

    def _open_report_path(self, panel_key: str, target: str) -> None:
        section = self.report_sections.get(panel_key)
        if section is None:
            self.show_info("当前还没有可打开的目录。")
            return
        path = section.result_dir if target == "result" else section.extra_dir
        self._open_path(path)

    def set_runtime_ref(self, runtime: Any) -> None:
        self._runtime_ref = runtime

    def _close_runtime(self) -> None:
        runtime = self._runtime_ref
        self._runtime_ref = None
        if runtime is None:
            return
        try:
            close_browser = getattr(runtime, "close_browser", None)
            if callable(close_browser):
                close_browser()
                return
            close = getattr(runtime, "close", None)
            if callable(close):
                close()
        except Exception:
            pass

    def closeEvent(self, event: QCloseEvent) -> None:
        self.queue_timer.stop()
        self._close_runtime()
        try:
            browser_dir = Path(tempfile.gettempdir()) / "_mcmod_browser_data"
            if browser_dir.exists():
                shutil.rmtree(browser_dir, ignore_errors=True)
        except Exception:
            pass
        cleanup_stale_import_workspaces()
        super().closeEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            local_paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
            if local_paths:
                event.acceptProposedAction()
                return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if not paths:
            event.ignore()
            return

        current_widget = self.stackedWidget.currentWidget()
        panel_key = "server" if current_widget is self.server_page else "mod"
        self._apply_dropped_paths(panel_key, paths)
        event.acceptProposedAction()

    def _apply_dropped_paths(self, panel_key: str, paths: List[str]) -> None:
        if not paths:
            return
        chosen = paths[0]
        if panel_key == "server":
            self.server_client_path_edit.setText(chosen)
            self.append_log("server", f"已拖入输入源：{chosen}")
        else:
            self.mod_path_edit.setText(chosen)
            self.append_log("mod", f"已拖入输入源：{chosen}")

        if len(paths) > 1:
            self.append_log(panel_key, f"检测到拖入了多个项目，本次先使用第一个：{chosen}")

        InfoBar.info(
            "已接收拖入文件",
            f"当前使用：{Path(chosen).name}",
            duration=1800,
            position=InfoBarPosition.TOP_RIGHT,
            parent=self,
        )


def main() -> None:
    app = QApplication.instance()
    created_app = False
    if app is None:
        app = QApplication(sys.argv)
        created_app = True

    app.setApplicationName(APP_TITLE)
    setTheme(Theme.DARK)
    setThemeColor(QColor("#22C55E"))

    window = App()
    window.show()

    if created_app:
        sys.exit(app.exec())
