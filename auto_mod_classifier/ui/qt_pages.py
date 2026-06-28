from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QSizePolicy, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CheckBox,
    ComboBox,
    FluentIcon as FIF,
    LineEdit,
    PlainTextEdit,
    PrimaryPushButton,
    ProgressBar,
    PushButton,
    StrongBodyLabel,
)

from ..download_support import build_idle_download_status_text
from ..shared import DOWNLOAD_SOURCE_OPTIONS, DOWNLOAD_SOURCE_SMART
from .qt_state import (
    HomeWidgets,
    ModInputWidgets,
    ReportSectionState,
    ServerInputWidgets,
    SettingsWidgets,
    TaskPanelState,
)
from .qt_theme import (
    INFO_COLOR,
    SECONDARY_TEXT_COLOR,
    SUCCESS_COLOR,
    TEXT_COLOR,
    WARNING_COLOR,
    apply_card_style,
    apply_input_style,
    apply_label_tone,
    apply_read_only_editor_style,
)
from .qt_widgets import ActionCard, MetricCard, ScrollablePage, StageBoard, StatusDot, TaskPage, build_result_table, build_tab_host


@dataclass
class HomePageBuild:
    page: TaskPage
    widgets: HomeWidgets


@dataclass
class ModPageBuild:
    page: TaskPage
    panel: TaskPanelState
    inputs: ModInputWidgets


@dataclass
class ServerPageBuild:
    page: TaskPage
    panel: TaskPanelState
    inputs: ServerInputWidgets


@dataclass
class ReportPageBuild:
    page: TaskPage
    sections: Dict[str, ReportSectionState]


@dataclass
class SettingsPageBuild:
    page: ScrollablePage
    widgets: SettingsWidgets


class QtPageFactory:
    """只负责页面搭建，不碰任务线程和事件队列。"""

    def __init__(self, app: QWidget):
        self.app = app

    def _create_card(self, title: str, description: str = "", *, variant: str = "panel") -> tuple[QFrame, QVBoxLayout]:
        card = QFrame(self.app)
        apply_card_style(card, variant)

        layout = QVBoxLayout(card)
        if variant == "subtle":
            layout.setContentsMargins(16, 16, 16, 16)
        else:
            layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        title_label = StrongBodyLabel(title, card)
        title_label.setStyleSheet(f"color: {TEXT_COLOR}; background: transparent; font-size: 14px; font-weight: 600;")
        layout.addWidget(title_label)

        if description:
            desc_label = BodyLabel(description, card)
            desc_label.setWordWrap(True)
            apply_label_tone(desc_label, muted=True, size=12)
            layout.addWidget(desc_label)

        return card, layout

    def _build_download_source_combo(self, current: str = DOWNLOAD_SOURCE_SMART) -> ComboBox:
        combo = ComboBox(self.app)
        for code, label in DOWNLOAD_SOURCE_OPTIONS:
            combo.addItem(label, userData=code)
            if code == current:
                combo.setCurrentIndex(combo.count() - 1)
        apply_input_style(combo)
        return combo

    def _add_control_row(self, layout: QVBoxLayout, title: str, control: QWidget, hint: str = "") -> None:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)
        title_label = BodyLabel(title, self.app)
        title_label.setFixedWidth(104)
        title_label.setStyleSheet(f"color: {SECONDARY_TEXT_COLOR}; background: transparent; font-size: 13px;")
        row.addWidget(title_label, 0, Qt.AlignVCenter)
        row.addWidget(control, 1)
        layout.addLayout(row)
        if hint:
            hint_label = BodyLabel(hint, self.app)
            hint_label.setWordWrap(True)
            apply_label_tone(hint_label, muted=True, size=12)
            layout.addWidget(hint_label)

    def _build_path_buttons(self, parent: QWidget, left_text: str, left_slot, right_text: str = "", right_slot=None) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)
        left_button = PushButton(left_text, parent)
        left_button.setObjectName("smallButton")
        left_button.clicked.connect(left_slot)
        row.addWidget(left_button)
        if right_text and right_slot:
            right_button = PushButton(right_text, parent)
            right_button.setObjectName("smallButton")
            right_button.clicked.connect(right_slot)
            row.addWidget(right_button)
        row.addStretch(1)
        return row

    def _build_task_workspace(self, page: TaskPage) -> tuple[QWidget, QVBoxLayout, QWidget, QVBoxLayout]:
        workspace = QWidget(page)
        workspace_layout = QHBoxLayout(workspace)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(16)

        left_column = QWidget(workspace)
        left_column.setFixedWidth(320)
        left_layout = QVBoxLayout(left_column)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(16)

        right_column = QWidget(workspace)
        right_column.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        right_layout = QVBoxLayout(right_column)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(16)

        workspace_layout.addWidget(left_column, 4)
        workspace_layout.addWidget(right_column, 6)
        page.container_layout.addWidget(workspace, 1)
        return left_column, left_layout, right_column, right_layout

    def _build_status_card(
        self,
        title: str,
        ready_text: str,
        result_button_text: str,
        result_slot,
        report_slot,
        *,
        parent: QWidget,
    ) -> tuple[QFrame, StatusDot, StrongBodyLabel, BodyLabel, ProgressBar, BodyLabel, BodyLabel, PushButton, PushButton]:
        card, layout = self._create_card(title)
        card.setParent(parent)
        card.setMinimumHeight(128)

        body_row = QHBoxLayout()
        body_row.setContentsMargins(0, 0, 0, 0)
        body_row.setSpacing(16)

        left_block = QVBoxLayout()
        left_block.setContentsMargins(0, 0, 0, 0)
        left_block.setSpacing(8)

        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 0, 0, 0)
        status_row.setSpacing(8)
        status_dot = StatusDot(card)
        stage_label = StrongBodyLabel("当前阶段：等待开始", card)
        stage_label.setStyleSheet(f"color: {TEXT_COLOR}; background: transparent; font-size: 15px; font-weight: 600;")
        status_row.addWidget(status_dot, 0, Qt.AlignVCenter)
        status_row.addWidget(stage_label, 1)
        left_block.addLayout(status_row)

        status_label = BodyLabel(ready_text, card)
        status_label.setWordWrap(True)
        apply_label_tone(status_label, muted=True, size=12)
        left_block.addWidget(status_label)
        body_row.addLayout(left_block, 3)

        right_block = QVBoxLayout()
        right_block.setContentsMargins(0, 0, 0, 0)
        right_block.setSpacing(8)
        progress_bar = ProgressBar(card)
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        right_block.addWidget(progress_bar)

        download_label = BodyLabel(build_idle_download_status_text(), card)
        download_label.setWordWrap(True)
        download_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        apply_label_tone(download_label, muted=True, size=12)
        right_block.addWidget(download_label)

        output_label = BodyLabel("输出位置：尚未运行", card)
        output_label.setWordWrap(True)
        output_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        output_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        apply_label_tone(output_label, muted=True, size=12)
        right_block.addWidget(output_label)
        body_row.addLayout(right_block, 2)
        layout.addLayout(body_row)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        result_button = PushButton(result_button_text, card)
        result_button.setObjectName("smallButton")
        result_button.setEnabled(False)
        result_button.clicked.connect(result_slot)
        action_row.addWidget(result_button)

        report_button = PushButton("查看报告", card)
        report_button.setObjectName("smallButton")
        report_button.clicked.connect(report_slot)
        action_row.addWidget(report_button)
        action_row.addStretch(1)
        layout.addLayout(action_row)

        return card, status_dot, stage_label, status_label, progress_bar, download_label, output_label, result_button, report_button

    def _build_log_pages(
        self,
        parent: QWidget,
        *,
        with_result_table: bool,
    ) -> tuple[QWidget, PlainTextEdit, PlainTextEdit, QWidget | None, BodyLabel | None]:
        summary_page = QWidget(parent)
        summary_layout = QVBoxLayout(summary_page)
        summary_layout.setContentsMargins(0, 0, 0, 0)
        summary_edit = PlainTextEdit(summary_page)
        summary_edit.setReadOnly(True)
        summary_edit.setMaximumBlockCount(500)
        summary_edit.setPlainText("任务完成后显示摘要。")
        apply_read_only_editor_style(summary_edit)
        summary_layout.addWidget(summary_edit)

        log_page = QWidget(parent)
        log_layout = QVBoxLayout(log_page)
        log_layout.setContentsMargins(0, 0, 0, 0)
        log_edit = PlainTextEdit(log_page)
        log_edit.setReadOnly(True)
        log_edit.setMaximumBlockCount(1200)
        log_edit.setPlainText("等待任务开始。")
        apply_read_only_editor_style(log_edit, console=True)
        log_layout.addWidget(log_edit)

        if not with_result_table:
            return log_page, summary_edit, log_edit, None, None

        result_page = QWidget(parent)
        result_layout = QVBoxLayout(result_page)
        result_layout.setContentsMargins(0, 0, 0, 0)
        result_layout.setSpacing(8)

        hint_label = BodyLabel("任务完成后显示关键结果。", result_page)
        hint_label.setWordWrap(True)
        apply_label_tone(hint_label, muted=True, size=12)
        result_layout.addWidget(hint_label)

        result_table = build_result_table(result_page)
        result_layout.addWidget(result_table, 1)

        return result_page, summary_edit, log_edit, result_table, hint_label

    def build_home_page(self) -> HomePageBuild:
        page = TaskPage(
            "homePage",
            "工作台",
            "快速启动模组筛选、制作服务端，查看最近任务结果。",
            self.app,
        )

        section_title = StrongBodyLabel("开始工作", page)
        section_title.setStyleSheet(f"color: {TEXT_COLOR}; background: transparent; font-size: 14px; font-weight: 600;")
        page.container_layout.addWidget(section_title)

        quick_host = QWidget(page)
        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 0, 0, 0)
        action_row.setSpacing(16)
        quick_host.setLayout(action_row)

        mod_action = ActionCard("模组筛选", "分出服务端保留、纯客户端和待确认。", "开始筛选", quick_host, icon=FIF.ZIP_FOLDER, primary=True)
        mod_action.button.clicked.connect(lambda: self.app.open_page(self.app.mod_page))
        action_row.addWidget(mod_action, 1)

        server_action = ActionCard("一键开服", "从客户端或整合包制作服务端。", "开始制作", quick_host, icon=FIF.COMMAND_PROMPT)
        server_action.button.clicked.connect(lambda: self.app.open_page(self.app.server_page))
        action_row.addWidget(server_action, 1)

        report_action = ActionCard("结果报告", "查看最近结果、日志和输出目录。", "查看结果", quick_host, icon=FIF.DOCUMENT)
        report_action.button.clicked.connect(lambda: self.app.open_page(self.app.report_page))
        action_row.addWidget(report_action, 1)
        page.container_layout.addWidget(quick_host, 2)

        status_grid = QWidget(page)
        status_layout = QGridLayout(status_grid)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setHorizontalSpacing(16)
        status_layout.setVerticalSpacing(16)
        status_layout.setColumnStretch(0, 1)
        status_layout.setColumnStretch(1, 1)

        mod_card, mod_layout = self._create_card("模组筛选")
        mod_status_row = QHBoxLayout()
        mod_status_row.setContentsMargins(0, 0, 0, 0)
        mod_status_row.setSpacing(8)
        mod_status_dot = StatusDot(mod_card)
        mod_status_label = StrongBodyLabel("待运行", mod_card)
        mod_status_label.setStyleSheet(f"color: {TEXT_COLOR}; background: transparent; font-size: 14px; font-weight: 600;")
        mod_status_row.addWidget(mod_status_dot, 0, Qt.AlignVCenter)
        mod_status_row.addWidget(mod_status_label, 1)
        mod_time_label = BodyLabel("最近时间：暂无", mod_card)
        mod_output_label = BodyLabel("输出位置：暂无", mod_card)
        for label in (mod_time_label, mod_output_label):
            label.setWordWrap(True)
            apply_label_tone(label, muted=True, size=12)
        mod_layout.addLayout(mod_status_row)
        mod_layout.addWidget(mod_time_label)
        mod_layout.addWidget(mod_output_label)
        mod_layout.addStretch(1)
        mod_button_row = QHBoxLayout()
        mod_button_row.addStretch(1)
        mod_result_button = PushButton("查看结果", mod_card)
        mod_result_button.setObjectName("smallButton")
        mod_result_button.clicked.connect(lambda: self.app.open_page(self.app.report_page))
        mod_button_row.addWidget(mod_result_button)
        mod_again_button = PushButton("再次运行", mod_card)
        mod_again_button.setObjectName("smallButton")
        mod_again_button.clicked.connect(lambda: self.app.open_page(self.app.mod_page))
        mod_button_row.addWidget(mod_again_button)
        mod_layout.addLayout(mod_button_row)

        server_card, server_layout = self._create_card("一键开服")
        server_status_row = QHBoxLayout()
        server_status_row.setContentsMargins(0, 0, 0, 0)
        server_status_row.setSpacing(8)
        server_status_dot = StatusDot(server_card)
        server_status_label = StrongBodyLabel("待运行", server_card)
        server_status_label.setStyleSheet(f"color: {TEXT_COLOR}; background: transparent; font-size: 14px; font-weight: 600;")
        server_status_row.addWidget(server_status_dot, 0, Qt.AlignVCenter)
        server_status_row.addWidget(server_status_label, 1)
        server_time_label = BodyLabel("最近时间：暂无", server_card)
        server_output_label = BodyLabel("输出位置：暂无", server_card)
        for label in (server_time_label, server_output_label):
            label.setWordWrap(True)
            apply_label_tone(label, muted=True, size=12)
        server_layout.addLayout(server_status_row)
        server_layout.addWidget(server_time_label)
        server_layout.addWidget(server_output_label)
        server_layout.addStretch(1)
        server_button_row = QHBoxLayout()
        server_button_row.addStretch(1)
        server_result_button = PushButton("查看结果", server_card)
        server_result_button.setObjectName("smallButton")
        server_result_button.clicked.connect(lambda: self.app.open_page(self.app.report_page))
        server_button_row.addWidget(server_result_button)
        server_again_button = PushButton("再次运行", server_card)
        server_again_button.setObjectName("smallButton")
        server_again_button.clicked.connect(lambda: self.app.open_page(self.app.server_page))
        server_button_row.addWidget(server_again_button)
        server_layout.addLayout(server_button_row)

        status_layout.addWidget(mod_card, 0, 0)
        status_layout.addWidget(server_card, 0, 1)

        status_title = StrongBodyLabel("最近状态", page)
        status_title.setStyleSheet(f"color: {TEXT_COLOR}; background: transparent; font-size: 14px; font-weight: 600;")
        page.container_layout.addWidget(status_title)
        page.container_layout.addWidget(status_grid, 1)
        page.container_layout.addStretch(1)

        input_hint = BodyLabel("支持文件夹、.mrpack、.zip，可直接拖入窗口。", page)
        input_hint.setAlignment(Qt.AlignCenter)
        apply_label_tone(input_hint, muted=True, size=12)
        page.container_layout.addWidget(input_hint, 0)

        return HomePageBuild(
            page=page,
            widgets=HomeWidgets(
                mod_status_dot=mod_status_dot,
                mod_status_label=mod_status_label,
                mod_time_label=mod_time_label,
                mod_output_label=mod_output_label,
                server_status_dot=server_status_dot,
                server_status_label=server_status_label,
                server_time_label=server_time_label,
                server_output_label=server_output_label,
            ),
        )

    def build_mod_page(self) -> ModPageBuild:
        page = TaskPage(
            "modPage",
            "模组筛选",
            "选择输入源，启动筛选；运行状态、结果和日志固定显示在右侧。",
            self.app,
        )
        left_column, left_layout, right_column, right_layout = self._build_task_workspace(page)

        source_card, source_layout = self._create_card("输入源选择", "选择目录或整合包。", variant="subtle")
        source_card.setParent(left_column)
        mod_path_edit = LineEdit(source_card)
        mod_path_edit.setPlaceholderText("选择目录、.mrpack 或 .zip")
        mod_path_edit.setClearButtonEnabled(True)
        apply_input_style(mod_path_edit)
        source_layout.addWidget(mod_path_edit)
        source_layout.addLayout(self._build_path_buttons(source_card, "浏览目录", self.app.choose_mod_folder, "选择整合包", self.app.choose_mod_archive))
        drag_hint = BodyLabel("也可以直接把文件夹或整合包拖到窗口里。", source_card)
        apply_label_tone(drag_hint, muted=True, size=12)
        source_layout.addWidget(drag_hint)

        quick_card, quick_layout = self._create_card("本次任务", variant="subtle")
        quick_card.setParent(left_column)
        mod_dry_run_checkbox = CheckBox("仅试运行，不移动文件", quick_card)
        quick_layout.addWidget(mod_dry_run_checkbox)
        settings_button = PushButton("全局筛选规则可在设置中修改", quick_card)
        settings_button.setObjectName("smallButton")
        settings_button.clicked.connect(lambda: self.app.open_page(self.app.settings_page))
        quick_layout.addWidget(settings_button, 0, Qt.AlignLeft)

        mod_start_button = PrimaryPushButton("开始筛选", left_column)
        mod_start_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        mod_start_button.clicked.connect(self.app.start_mod_task)

        left_layout.addWidget(source_card)
        left_layout.addWidget(quick_card)
        left_layout.addStretch(1)
        left_layout.addWidget(mod_start_button)

        (
            status_card,
            mod_status_dot,
            mod_stage_label,
            mod_status_label,
            mod_progress_bar,
            mod_download_label,
            mod_output_label,
            mod_result_button,
            _mod_report_button,
        ) = self._build_status_card(
            "运行状态",
            "请选择输入源，然后开始筛选。",
            "打开结果目录",
            lambda: self.app.open_panel_path("mod", "result"),
            lambda: self.app.open_page(self.app.report_page),
            parent=right_column,
        )
        right_layout.addWidget(status_card, 2)

        mod_stage_board = StageBoard(
            "进度与分类",
            [
                ("scan", "读取目录"),
                ("classify", "首轮筛选"),
                ("second-pass", "补查确认"),
                ("complete", "完成"),
            ],
            right_column,
        )

        metric_row = QHBoxLayout()
        metric_row.setSpacing(12)
        mod_keep_card = MetricCard("服务端保留", "--", "可留在服务端", accent_color=INFO_COLOR)
        mod_client_card = MetricCard("纯客户端", "--", "可从服务端移出", accent_color=SUCCESS_COLOR)
        mod_unknown_card = MetricCard("待确认", "--", "建议查看", accent_color=WARNING_COLOR)
        metric_row.addWidget(mod_keep_card, 1)
        metric_row.addWidget(mod_client_card, 1)
        metric_row.addWidget(mod_unknown_card, 1)
        board_layout = mod_stage_board.layout()
        if isinstance(board_layout, QVBoxLayout):
            board_layout.addLayout(metric_row)
        right_layout.addWidget(mod_stage_board, 3)

        preview_card, preview_layout = self._create_card("结果与日志")
        preview_card.setParent(right_column)
        result_page, mod_summary_edit, mod_log_edit, mod_result_table, mod_result_hint_label = self._build_log_pages(
            preview_card,
            with_result_table=True,
        )
        summary_page = mod_summary_edit.parentWidget()
        log_page = mod_log_edit.parentWidget()
        tab_host, _, _ = build_tab_host(
            preview_card,
            [
                ("results", "结果预览", result_page),
                ("summary", "任务摘要", summary_page),
                ("logs", "实时日志", log_page),
            ],
        )
        preview_layout.addWidget(tab_host)
        right_layout.addWidget(preview_card, 5)

        assert mod_result_table is not None
        assert mod_result_hint_label is not None
        return ModPageBuild(
            page=page,
            panel=TaskPanelState(
                status_dot=mod_status_dot,
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
            ),
            inputs=ModInputWidgets(path_edit=mod_path_edit, dry_run_checkbox=mod_dry_run_checkbox),
        )

    def build_server_page(self) -> ServerPageBuild:
        page = TaskPage(
            "serverPage",
            "一键开服",
            "选择客户端输入源和服务端输出目录；制作过程固定显示在右侧。",
            self.app,
        )
        left_column, left_layout, right_column, right_layout = self._build_task_workspace(page)

        source_card, source_layout = self._create_card("客户端输入源", "选择客户端目录或整合包。", variant="subtle")
        source_card.setParent(left_column)
        server_client_path_edit = LineEdit(source_card)
        server_client_path_edit.setPlaceholderText("选择客户端目录、.mrpack 或 .zip")
        server_client_path_edit.setClearButtonEnabled(True)
        apply_input_style(server_client_path_edit)
        source_layout.addWidget(server_client_path_edit)
        source_layout.addLayout(self._build_path_buttons(source_card, "浏览目录", self.app.choose_client_folder, "选择整合包", self.app.choose_server_archive))

        output_card, output_layout = self._create_card("服务端输出目录", "建议选择新的空目录。", variant="subtle")
        output_card.setParent(left_column)
        server_output_path_edit = LineEdit(output_card)
        server_output_path_edit.setPlaceholderText("选择服务端输出目录")
        server_output_path_edit.setClearButtonEnabled(True)
        apply_input_style(server_output_path_edit)
        output_layout.addWidget(server_output_path_edit)
        output_layout.addLayout(self._build_path_buttons(output_card, "浏览输出目录", self.app.choose_output_folder))

        settings_card, settings_layout = self._create_card("本次任务", variant="subtle")
        settings_card.setParent(left_column)
        settings_button = PushButton("全局开服默认设置可在设置中修改", settings_card)
        settings_button.setObjectName("smallButton")
        settings_button.clicked.connect(lambda: self.app.open_page(self.app.settings_page))
        settings_layout.addWidget(settings_button, 0, Qt.AlignLeft)

        server_start_button = PrimaryPushButton("开始制作", left_column)
        server_start_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        server_start_button.clicked.connect(self.app.start_server_task)

        left_layout.addWidget(source_card)
        left_layout.addWidget(output_card)
        left_layout.addWidget(settings_card)
        left_layout.addStretch(1)
        left_layout.addWidget(server_start_button)

        (
            status_card,
            server_status_dot,
            server_stage_label,
            server_status_label,
            server_progress_bar,
            server_download_label,
            server_output_label,
            server_result_button,
            _server_report_button,
        ) = self._build_status_card(
            "运行状态",
            "请选择客户端输入源和输出目录，然后开始制作。",
            "打开服务端目录",
            lambda: self.app.open_panel_path("server", "result"),
            lambda: self.app.open_page(self.app.report_page),
            parent=right_column,
        )
        right_layout.addWidget(status_card, 2)

        server_stage_board = StageBoard(
            "开服阶段",
            [
                ("scan", "识别客户端"),
                ("precheck", "匹配 Java"),
                ("installer", "下载安装器"),
                ("install", "安装服务端"),
                ("classify", "筛选模组"),
                ("verify", "启动验证"),
            ],
            right_column,
        )
        right_layout.addWidget(server_stage_board, 3)

        preview_card, preview_layout = self._create_card("摘要与日志")
        preview_card.setParent(right_column)
        _log_page, server_summary_edit, server_log_edit, _table, _hint = self._build_log_pages(
            preview_card,
            with_result_table=False,
        )
        summary_page = server_summary_edit.parentWidget()
        log_page = server_log_edit.parentWidget()
        tab_host, _, _ = build_tab_host(
            preview_card,
            [
                ("summary", "任务摘要", summary_page),
                ("logs", "实时日志", log_page),
            ],
        )
        preview_layout.addWidget(tab_host)
        right_layout.addWidget(preview_card, 5)

        server_extra_button = PushButton("打开日志目录", status_card)
        server_extra_button.setObjectName("smallButton")
        server_extra_button.setEnabled(False)
        server_extra_button.clicked.connect(lambda: self.app.open_panel_path("server", "extra"))
        status_layout = status_card.layout()
        if status_layout is not None:
            action_item = status_layout.itemAt(status_layout.count() - 1)
            action_layout = action_item.layout() if action_item is not None else None
            if isinstance(action_layout, QHBoxLayout):
                action_layout.insertWidget(2, server_extra_button)
            else:
                status_layout.addWidget(server_extra_button, 0, Qt.AlignLeft)

        return ServerPageBuild(
            page=page,
            panel=TaskPanelState(
                status_dot=server_status_dot,
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
            ),
            inputs=ServerInputWidgets(client_path_edit=server_client_path_edit, output_path_edit=server_output_path_edit),
        )

    def build_report_page(self) -> ReportPageBuild:
        page = TaskPage(
            "reportPage",
            "结果报告",
            "回看最近一次模组筛选和服务端制作结果。",
            self.app,
        )
        grid = QWidget(page)
        grid_layout = QGridLayout(grid)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setHorizontalSpacing(12)
        grid_layout.setVerticalSpacing(12)
        grid_layout.setColumnStretch(0, 1)
        grid_layout.setColumnStretch(1, 1)

        mod_card, mod_layout = self._create_card("模组筛选结果")
        mod_status_row = QHBoxLayout()
        mod_status_row.setContentsMargins(0, 0, 0, 0)
        mod_status_row.setSpacing(8)
        mod_status_dot = StatusDot(mod_card)
        mod_status = StrongBodyLabel("还没有最近结果", mod_card)
        mod_status.setStyleSheet(f"color: {TEXT_COLOR}; background: transparent; font-size: 14px; font-weight: 600;")
        mod_status_row.addWidget(mod_status_dot, 0, Qt.AlignVCenter)
        mod_status_row.addWidget(mod_status, 1)
        mod_time = BodyLabel("最近时间：暂无", mod_card)
        mod_summary = PlainTextEdit(mod_card)
        mod_summary.setReadOnly(True)
        mod_summary.setMinimumHeight(136)
        mod_summary.setMaximumHeight(168)
        mod_summary.setPlainText("完成一次筛选后显示摘要。")
        apply_read_only_editor_style(mod_summary)
        mod_time.setWordWrap(True)
        apply_label_tone(mod_time, muted=True, size=12)
        mod_layout.addLayout(mod_status_row)
        mod_layout.addWidget(mod_time)
        mod_layout.addWidget(mod_summary)
        mod_buttons = QHBoxLayout()
        mod_buttons.addStretch(1)
        mod_result_button = PushButton("打开目录", mod_card)
        mod_result_button.setObjectName("smallButton")
        mod_result_button.setEnabled(False)
        mod_result_button.clicked.connect(lambda: self.app.open_report_path("mod", "result"))
        mod_buttons.addWidget(mod_result_button)
        mod_log_button = PushButton("查看日志", mod_card)
        mod_log_button.setObjectName("smallButton")
        mod_log_button.clicked.connect(lambda: self.app.open_page(self.app.mod_page))
        mod_buttons.addWidget(mod_log_button)
        mod_page_button = PushButton("返回页面", mod_card)
        mod_page_button.setObjectName("smallButton")
        mod_page_button.clicked.connect(lambda: self.app.open_page(self.app.mod_page))
        mod_buttons.addWidget(mod_page_button)
        mod_layout.addLayout(mod_buttons)

        server_card, server_layout = self._create_card("一键开服结果")
        server_status_row = QHBoxLayout()
        server_status_row.setContentsMargins(0, 0, 0, 0)
        server_status_row.setSpacing(8)
        server_status_dot = StatusDot(server_card)
        server_status = StrongBodyLabel("还没有最近结果", server_card)
        server_status.setStyleSheet(f"color: {TEXT_COLOR}; background: transparent; font-size: 14px; font-weight: 600;")
        server_status_row.addWidget(server_status_dot, 0, Qt.AlignVCenter)
        server_status_row.addWidget(server_status, 1)
        server_time = BodyLabel("最近时间：暂无", server_card)
        server_summary = PlainTextEdit(server_card)
        server_summary.setReadOnly(True)
        server_summary.setMinimumHeight(136)
        server_summary.setMaximumHeight(168)
        server_summary.setPlainText("完成一次制作后显示摘要。")
        apply_read_only_editor_style(server_summary)
        server_time.setWordWrap(True)
        apply_label_tone(server_time, muted=True, size=12)
        server_layout.addLayout(server_status_row)
        server_layout.addWidget(server_time)
        server_layout.addWidget(server_summary)
        server_buttons = QHBoxLayout()
        server_buttons.addStretch(1)
        server_result_button = PushButton("打开目录", server_card)
        server_result_button.setObjectName("smallButton")
        server_result_button.setEnabled(False)
        server_result_button.clicked.connect(lambda: self.app.open_report_path("server", "result"))
        server_buttons.addWidget(server_result_button)
        server_extra_button = PushButton("查看日志", server_card)
        server_extra_button.setObjectName("smallButton")
        server_extra_button.setEnabled(False)
        server_extra_button.clicked.connect(lambda: self.app.open_report_path("server", "extra"))
        server_buttons.addWidget(server_extra_button)
        server_page_button = PushButton("返回页面", server_card)
        server_page_button.setObjectName("smallButton")
        server_page_button.clicked.connect(lambda: self.app.open_page(self.app.server_page))
        server_buttons.addWidget(server_page_button)
        server_layout.addLayout(server_buttons)

        grid_layout.addWidget(mod_card, 0, 0)
        grid_layout.addWidget(server_card, 0, 1)
        page.container_layout.addWidget(grid)
        page.container_layout.addStretch(1)

        return ReportPageBuild(
            page=page,
            sections={
                "mod": ReportSectionState(
                    status_dot=mod_status_dot,
                    status_label=mod_status,
                    time_label=mod_time,
                    summary_edit=mod_summary,
                    result_button=mod_result_button,
                    extra_button=None,
                ),
                "server": ReportSectionState(
                    status_dot=server_status_dot,
                    status_label=server_status,
                    time_label=server_time,
                    summary_edit=server_summary,
                    result_button=server_result_button,
                    extra_button=server_extra_button,
                ),
            },
        )

    def build_settings_page(self) -> SettingsPageBuild:
        page = ScrollablePage(
            "settingsPage",
            "设置",
            "调整筛选规则、开服默认值、缓存和界面偏好。",
            self.app,
        )
        grid = QWidget(page)
        grid_layout = QGridLayout(grid)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setHorizontalSpacing(12)
        grid_layout.setVerticalSpacing(12)
        grid_layout.setColumnStretch(0, 1)
        grid_layout.setColumnStretch(1, 1)

        filter_card, filter_layout = self._create_card("筛选规则设置", "影响模组筛选和开服时的模组处理。")
        filter_download_source_combo = self._build_download_source_combo()
        self._add_control_row(filter_layout, "下载源", filter_download_source_combo)
        filter_use_mcmod_checkbox = CheckBox("需要时查询 MC百科", filter_card)
        filter_use_mcmod_checkbox.setChecked(True)
        filter_use_cf_checkbox = CheckBox("需要时查询 CurseForge", filter_card)
        filter_second_pass_checkbox = CheckBox("启用补查确认", filter_card)
        filter_manual_review_checkbox = CheckBox("保留人工确认提示", filter_card)
        filter_manual_review_checkbox.setChecked(True)
        for checkbox in (
            filter_use_mcmod_checkbox,
            filter_use_cf_checkbox,
            filter_second_pass_checkbox,
            filter_manual_review_checkbox,
        ):
            filter_layout.addWidget(checkbox)

        server_card, server_layout = self._create_card("开服默认设置", "制作服务端时优先使用这些默认值。")
        server_output_path_edit = LineEdit(server_card)
        server_output_path_edit.setPlaceholderText("默认输出目录")
        server_output_path_edit.setClearButtonEnabled(True)
        apply_input_style(server_output_path_edit)
        self._add_control_row(server_layout, "默认输出目录", server_output_path_edit, "浏览输出目录时会优先打开这里。")
        server_download_source_combo = self._build_download_source_combo()
        self._add_control_row(server_layout, "默认下载源", server_download_source_combo)
        java_rule_combo = ComboBox(server_card)
        for text in ("自动匹配", "优先使用本机 Java", "只使用客户端自带 Java"):
            java_rule_combo.addItem(text)
        apply_input_style(java_rule_combo)
        self._add_control_row(server_layout, "Java 匹配方式", java_rule_combo)

        cache_card, cache_layout = self._create_card("缓存与存储")
        cache_path_edit = LineEdit(cache_card)
        cache_path_edit.setPlaceholderText("使用系统临时目录")
        cache_path_edit.setClearButtonEnabled(True)
        apply_input_style(cache_path_edit)
        self._add_control_row(cache_layout, "缓存路径", cache_path_edit)
        cache_auto_cleanup_checkbox = CheckBox("启动和退出时自动清理临时缓存", cache_card)
        cache_auto_cleanup_checkbox.setChecked(True)
        cache_layout.addWidget(cache_auto_cleanup_checkbox)
        cleanup_button = PushButton("清理整合包缓存", cache_card)
        cleanup_button.setObjectName("warningButton")
        cleanup_button.clicked.connect(self.app.cleanup_import_cache)
        cache_layout.addWidget(cleanup_button, 0, Qt.AlignLeft)

        interface_card, interface_layout = self._create_card("界面设置")
        theme_combo = ComboBox(interface_card)
        for text in ("深色模式", "浅色模式"):
            theme_combo.addItem(text)
        apply_input_style(theme_combo)
        self._add_control_row(interface_layout, "主题", theme_combo)
        scale_combo = ComboBox(interface_card)
        for text in ("100%", "110%", "125%"):
            scale_combo.addItem(text)
        apply_input_style(scale_combo)
        self._add_control_row(interface_layout, "缩放比例", scale_combo)
        detail_log_checkbox = CheckBox("显示详细日志", interface_card)
        detail_log_checkbox.setChecked(True)
        animation_checkbox = CheckBox("启用界面动效", interface_card)
        animation_checkbox.setChecked(True)
        interface_layout.addWidget(detail_log_checkbox)
        interface_layout.addWidget(animation_checkbox)

        about_card, about_layout = self._create_card("关于", variant="subtle")
        about_card.setMaximumHeight(82)
        about_layout.setSpacing(4)
        version_label = BodyLabel("版本：3.0", about_card)
        version_label.setWordWrap(True)
        apply_label_tone(version_label, muted=True, size=12)
        about_layout.addWidget(version_label)

        grid_layout.addWidget(filter_card, 0, 0)
        grid_layout.addWidget(server_card, 0, 1)
        grid_layout.addWidget(cache_card, 1, 0)
        grid_layout.addWidget(interface_card, 1, 1)
        grid_layout.addWidget(about_card, 2, 0, 1, 2)
        page.container_layout.addWidget(grid)
        page.container_layout.addStretch(1)

        return SettingsPageBuild(
            page=page,
            widgets=SettingsWidgets(
                filter_download_source_combo=filter_download_source_combo,
                filter_use_mcmod_checkbox=filter_use_mcmod_checkbox,
                filter_use_cf_checkbox=filter_use_cf_checkbox,
                filter_second_pass_checkbox=filter_second_pass_checkbox,
                filter_manual_review_checkbox=filter_manual_review_checkbox,
                server_output_path_edit=server_output_path_edit,
                server_download_source_combo=server_download_source_combo,
                java_rule_combo=java_rule_combo,
                cache_path_edit=cache_path_edit,
                cache_auto_cleanup_checkbox=cache_auto_cleanup_checkbox,
                theme_combo=theme_combo,
                scale_combo=scale_combo,
                detail_log_checkbox=detail_log_checkbox,
                animation_checkbox=animation_checkbox,
            ),
        )
