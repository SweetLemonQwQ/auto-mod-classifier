from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Dict, Optional

import qfluentwidgets
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QSplitter, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CheckBox,
    ComboBox,
    LineEdit,
    PlainTextEdit,
    PrimaryPushButton,
    ProgressBar,
    PushButton,
    StrongBodyLabel,
)

from ..download_support import build_idle_download_status_text
from ..shared import DOWNLOAD_SOURCE_OPTIONS
from .qt_state import (
    HomeWidgets,
    ModInputWidgets,
    ReportSectionState,
    ServerInputWidgets,
    TaskPanelState,
)
from .qt_theme import TEXT_COLOR, apply_card_style, apply_input_style, apply_label_tone, apply_read_only_editor_style
from .qt_widgets import MetricCard, ScrollablePage, StageBoard, build_result_table, build_tab_host


@dataclass
class HomePageBuild:
    page: ScrollablePage
    widgets: HomeWidgets


@dataclass
class ModPageBuild:
    page: ScrollablePage
    panel: TaskPanelState
    inputs: ModInputWidgets


@dataclass
class ServerPageBuild:
    page: ScrollablePage
    panel: TaskPanelState
    inputs: ServerInputWidgets


@dataclass
class ReportPageBuild:
    page: ScrollablePage
    sections: Dict[str, ReportSectionState]


class QtPageFactory:
    """只负责页面搭建，不碰任务线程和事件队列。"""

    def __init__(self, app: QWidget):
        self.app = app

    def _create_card(self, title: str, description: str = "", *, variant: str = "panel") -> tuple[QFrame, QVBoxLayout]:
        card = QFrame(self.app)
        apply_card_style(card, variant)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        title_label = StrongBodyLabel(title, card)
        title_label.setStyleSheet(f"color: {TEXT_COLOR}; background: transparent;")
        layout.addWidget(title_label)

        if description:
            desc_label = BodyLabel(description, card)
            desc_label.setWordWrap(True)
            apply_label_tone(desc_label, muted=True)
            layout.addWidget(desc_label)

        return card, layout

    def _build_download_source_combo(self) -> ComboBox:
        combo = ComboBox(self.app)
        for code, label in DOWNLOAD_SOURCE_OPTIONS:
            combo.addItem(label, userData=code)
            if code == "smart":
                combo.setCurrentIndex(combo.count() - 1)
        return combo

    def build_home_page(self) -> HomePageBuild:
        page = ScrollablePage(
            "homePage",
            "工作台",
            "这里不是欢迎页，而是入口工作台。你直接从这里进入筛模组、做服务端，或者回看最近结果。",
            self.app,
        )
        dashboard = QWidget(page)
        dashboard_layout = QGridLayout(dashboard)
        dashboard_layout.setContentsMargins(0, 0, 0, 0)
        dashboard_layout.setHorizontalSpacing(16)
        dashboard_layout.setVerticalSpacing(16)
        dashboard_layout.setColumnStretch(0, 3)
        dashboard_layout.setColumnStretch(1, 2)

        quick_card, quick_layout = self._create_card(
            "开始工作",
            "支持目录、客户端、mrpack、CurseForge 风格 zip 直接导入，也支持把文件夹或整合包拖进窗口。",
            variant="hero",
        )
        quick_button_row = QHBoxLayout()
        quick_button_row.setSpacing(12)

        mod_button = PrimaryPushButton("进入模组筛选", quick_card)
        mod_button.clicked.connect(lambda: self.app.open_page(self.app.mod_page))
        quick_button_row.addWidget(mod_button)

        server_button = PushButton("进入一键开服", quick_card)
        server_button.clicked.connect(lambda: self.app.open_page(self.app.server_page))
        quick_button_row.addWidget(server_button)

        report_button = PushButton("查看结果报告", quick_card)
        report_button.clicked.connect(lambda: self.app.open_page(self.app.report_page))
        quick_button_row.addWidget(report_button)
        quick_button_row.addStretch(1)
        quick_layout.addLayout(quick_button_row)

        drag_hint = BodyLabel("拖进来的整合包会自动走导入整理流程，不需要你手动展开。", quick_card)
        drag_hint.setWordWrap(True)
        apply_label_tone(drag_hint, muted=True)
        quick_layout.addWidget(drag_hint)

        status_card, status_layout = self._create_card(
            "最近状态",
            "这里同步两条主流程最近一次的状态和输出位置，方便直接决定下一步该去哪一页。",
        )
        mod_status_label = StrongBodyLabel("模组筛选：待运行", status_card)
        mod_status_label.setStyleSheet(f"color: {TEXT_COLOR}; background: transparent;")
        mod_output_label = BodyLabel("最近输出：尚无结果", status_card)
        mod_output_label.setWordWrap(True)
        apply_label_tone(mod_output_label, muted=True)
        status_layout.addWidget(mod_status_label)
        status_layout.addWidget(mod_output_label)

        status_button_row = QHBoxLayout()
        status_button_row.setSpacing(10)
        open_mod_page_button = PushButton("打开模组筛选页", status_card)
        open_mod_page_button.clicked.connect(lambda: self.app.open_page(self.app.mod_page))
        status_button_row.addWidget(open_mod_page_button)
        open_server_page_button = PushButton("打开一键开服页", status_card)
        open_server_page_button.clicked.connect(lambda: self.app.open_page(self.app.server_page))
        status_button_row.addWidget(open_server_page_button)
        status_button_row.addStretch(1)
        status_layout.addLayout(status_button_row)

        divider = QFrame(status_card)
        divider.setFixedHeight(1)
        divider.setStyleSheet("border: 0; background-color: #334155;")
        status_layout.addWidget(divider)

        server_status_label = StrongBodyLabel("一键开服：待运行", status_card)
        server_status_label.setStyleSheet(f"color: {TEXT_COLOR}; background: transparent;")
        server_output_label = BodyLabel("最近输出：尚无结果", status_card)
        server_output_label.setWordWrap(True)
        apply_label_tone(server_output_label, muted=True)
        status_layout.addWidget(server_status_label)
        status_layout.addWidget(server_output_label)

        inputs_card, inputs_layout = self._create_card(
            "支持输入",
            "当前项目已经把整合包导入和核心业务拆开了，所以你现在不用先自己整理客户端目录。",
        )
        for text in [
            "目录、zip、mrpack 都可以直接扔进来。",
            "智能优选会比较 MCIM、BMCLAPI 和官方源。",
            "模组筛选和一键开服共用同一套任务入口，不重复走两套逻辑。",
        ]:
            label = BodyLabel(f"• {text}", inputs_card)
            label.setWordWrap(True)
            apply_label_tone(label, muted=True)
            inputs_layout.addWidget(label)

        capability_card, capability_layout = self._create_card(
            "现在这版重点",
            "页面已经固定成桌面工具工作台，核心信息都在首屏，不再做成长滚动说明页。",
        )
        for text in [
            "筛模组页右侧固定看阶段条、统计卡、结果预览和日志。",
            "一键开服页右侧固定看版本识别、安装流程和启动验证。",
            "结果报告页负责集中打开结果目录和日志目录。",
            "版本选择、人工核查这些阻塞交互已经切到 Qt 弹窗。",
        ]:
            label = BodyLabel(f"• {text}", capability_card)
            label.setWordWrap(True)
            apply_label_tone(label, muted=True)
            capability_layout.addWidget(label)

        dashboard_layout.addWidget(quick_card, 0, 0)
        dashboard_layout.addWidget(status_card, 0, 1)
        dashboard_layout.addWidget(inputs_card, 1, 0)
        dashboard_layout.addWidget(capability_card, 1, 1)

        page.container_layout.addWidget(dashboard)
        page.container_layout.addStretch(1)

        return HomePageBuild(
            page=page,
            widgets=HomeWidgets(
                mod_status_label=mod_status_label,
                mod_output_label=mod_output_label,
                server_status_label=server_status_label,
                server_output_label=server_output_label,
            ),
        )

    def build_mod_page(self) -> ModPageBuild:
        page = ScrollablePage(
            "modPage",
            "模组筛选",
            "输入目录或整合包后，左侧负责参数和操作，右侧专门盯运行状态、阶段推进、结果预览和日志。",
            self.app,
        )
        workspace = QSplitter(Qt.Horizontal, page)
        workspace.setChildrenCollapsible(False)
        workspace.setHandleWidth(1)
        workspace.setStyleSheet("QSplitter::handle { background: #0F172A; }")

        left_column = QWidget(workspace)
        left_column.setMinimumWidth(360)
        left_column.setMaximumWidth(420)
        left_layout = QVBoxLayout(left_column)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(16)

        source_card, source_layout = self._create_card("输入源", "支持目录、mrpack、zip，也支持直接拖入窗口。", variant="hero")
        mod_path_edit = LineEdit(source_card)
        mod_path_edit.setPlaceholderText("选择 mods 目录、客户端目录或整合包")
        mod_path_edit.setClearButtonEnabled(True)
        apply_input_style(mod_path_edit)
        source_layout.addWidget(mod_path_edit)

        source_button_row = QHBoxLayout()
        source_button_row.setSpacing(10)
        mod_folder_button = PushButton("浏览目录", source_card)
        mod_folder_button.clicked.connect(self.app.choose_mod_folder)
        source_button_row.addWidget(mod_folder_button)

        mod_archive_button = PushButton("选择整合包", source_card)
        mod_archive_button.clicked.connect(self.app.choose_mod_archive)
        source_button_row.addWidget(mod_archive_button)
        source_layout.addLayout(source_button_row)

        options_card, options_layout = self._create_card(
            "筛选策略",
            "默认先走本地元数据判断，不够再补查远程来源。智能优选会在 MCIM、BMCLAPI、官方源之间自动挑路线。",
        )
        download_title = StrongBodyLabel("下载源", options_card)
        download_title.setStyleSheet(f"color: {TEXT_COLOR}; background: transparent;")
        options_layout.addWidget(download_title)

        mod_download_source_combo = self._build_download_source_combo()
        apply_input_style(mod_download_source_combo)
        options_layout.addWidget(mod_download_source_combo)

        mod_dry_run_checkbox = CheckBox("仅试运行，不移动模组", options_card)
        mod_use_mcmod_checkbox = CheckBox("启用 MC百科（可能需要人工验证码）", options_card)
        mod_use_mcmod_checkbox.setChecked(True)
        mod_use_cf_checkbox = CheckBox("启用 CurseForge（测试版）", options_card)
        mod_second_pass_checkbox = CheckBox("启用 2 次筛选补查", options_card)
        for checkbox in (
            mod_dry_run_checkbox,
            mod_use_mcmod_checkbox,
            mod_use_cf_checkbox,
            mod_second_pass_checkbox,
        ):
            options_layout.addWidget(checkbox)

        mod_start_button = PrimaryPushButton("开始筛选", options_card)
        mod_start_button.clicked.connect(self.app.start_mod_task)
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
            apply_label_tone(label, muted=True)
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
        mod_stage_label.setStyleSheet(f"color: {TEXT_COLOR}; background: transparent;")
        status_layout.addWidget(mod_stage_label)

        mod_status_label = BodyLabel("请选择输入源，然后开始筛选。", status_card)
        mod_status_label.setWordWrap(True)
        apply_label_tone(mod_status_label, muted=True)
        status_layout.addWidget(mod_status_label)

        mod_progress_bar = ProgressBar(status_card)
        mod_progress_bar.setRange(0, 100)
        mod_progress_bar.setValue(0)
        status_layout.addWidget(mod_progress_bar)

        mod_download_label = BodyLabel(build_idle_download_status_text(), status_card)
        mod_download_label.setWordWrap(True)
        apply_label_tone(mod_download_label, muted=True)
        status_layout.addWidget(mod_download_label)

        mod_output_label = BodyLabel("输出位置：尚未运行", status_card)
        mod_output_label.setWordWrap(True)
        mod_output_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        apply_label_tone(mod_output_label, muted=True)
        status_layout.addWidget(mod_output_label)

        mod_action_row = QHBoxLayout()
        mod_result_button = PushButton("打开结果目录", status_card)
        mod_result_button.setEnabled(False)
        mod_result_button.clicked.connect(lambda: self.app.open_panel_path("mod", "result"))
        mod_action_row.addWidget(mod_result_button)
        mod_report_button = PushButton("查看结果报告", status_card)
        mod_report_button.clicked.connect(lambda: self.app.open_page(self.app.report_page))
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
        apply_label_tone(mod_result_hint_label, muted=True)
        result_layout.addWidget(mod_result_hint_label)

        mod_result_table = build_result_table(result_page)
        result_layout.addWidget(mod_result_table)

        summary_page = QWidget(preview_card)
        summary_layout = QVBoxLayout(summary_page)
        summary_layout.setContentsMargins(0, 0, 0, 0)
        mod_summary_edit = PlainTextEdit(summary_page)
        mod_summary_edit.setReadOnly(True)
        mod_summary_edit.setPlainText("任务完成后，这里会展示结果摘要、输出目录和报告路径。")
        apply_read_only_editor_style(mod_summary_edit)
        summary_layout.addWidget(mod_summary_edit)

        log_page = QWidget(preview_card)
        log_layout = QVBoxLayout(log_page)
        log_layout.setContentsMargins(0, 0, 0, 0)
        mod_log_edit = PlainTextEdit(log_page)
        mod_log_edit.setReadOnly(True)
        mod_log_edit.setPlainText("实时日志会滚动显示在这里。")
        apply_read_only_editor_style(mod_log_edit, console=True)
        log_layout.addWidget(mod_log_edit)

        tab_host, _, _ = build_tab_host(
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

        return ModPageBuild(
            page=page,
            panel=TaskPanelState(
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
            inputs=ModInputWidgets(
                path_edit=mod_path_edit,
                download_source_combo=mod_download_source_combo,
                dry_run_checkbox=mod_dry_run_checkbox,
                use_mcmod_checkbox=mod_use_mcmod_checkbox,
                use_cf_checkbox=mod_use_cf_checkbox,
                second_pass_checkbox=mod_second_pass_checkbox,
            ),
        )

    def build_server_page(self) -> ServerPageBuild:
        page = ScrollablePage(
            "serverPage",
            "一键开服",
            "左侧准备输入和参数，右侧专门盯版本识别、安装阶段、启动验证和完整日志。",
            self.app,
        )
        workspace = QSplitter(Qt.Horizontal, page)
        workspace.setChildrenCollapsible(False)
        workspace.setHandleWidth(1)
        workspace.setStyleSheet("QSplitter::handle { background: #0F172A; }")

        left_column = QWidget(workspace)
        left_column.setMinimumWidth(360)
        left_column.setMaximumWidth(420)
        left_layout = QVBoxLayout(left_column)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(16)

        source_card, source_layout = self._create_card("客户端输入源", "支持完整客户端目录、mrpack、CurseForge 风格 zip。", variant="hero")
        server_client_path_edit = LineEdit(source_card)
        server_client_path_edit.setPlaceholderText("选择客户端目录或整合包")
        server_client_path_edit.setClearButtonEnabled(True)
        apply_input_style(server_client_path_edit)
        source_layout.addWidget(server_client_path_edit)

        source_button_row = QHBoxLayout()
        source_button_row.setSpacing(10)
        client_folder_button = PushButton("浏览目录", source_card)
        client_folder_button.clicked.connect(self.app.choose_client_folder)
        source_button_row.addWidget(client_folder_button)

        client_archive_button = PushButton("选择整合包", source_card)
        client_archive_button.clicked.connect(self.app.choose_server_archive)
        source_button_row.addWidget(client_archive_button)
        source_layout.addLayout(source_button_row)

        output_card, output_layout = self._create_card("服务端输出目录", "建议先新建一个空目录，避免和现有文件混在一起。")
        server_output_path_edit = LineEdit(output_card)
        server_output_path_edit.setPlaceholderText("选择新的空服务端输出目录")
        server_output_path_edit.setClearButtonEnabled(True)
        apply_input_style(server_output_path_edit)
        output_layout.addWidget(server_output_path_edit)

        output_button = PushButton("浏览输出目录", output_card)
        output_button.clicked.connect(self.app.choose_output_folder)
        output_layout.addWidget(output_button)

        options_card, options_layout = self._create_card(
            "开服策略",
            "整合包会先被整理成本地客户端工作区，再走版本识别、安装器下载、服务端安装、模组筛选和两次启动验证。",
        )
        download_title = StrongBodyLabel("下载源", options_card)
        download_title.setStyleSheet(f"color: {TEXT_COLOR}; background: transparent;")
        options_layout.addWidget(download_title)

        server_download_source_combo = self._build_download_source_combo()
        apply_input_style(server_download_source_combo)
        options_layout.addWidget(server_download_source_combo)

        server_use_mcmod_checkbox = CheckBox("启用 MC百科（可能需要人工验证码）", options_card)
        server_use_mcmod_checkbox.setChecked(True)
        server_use_cf_checkbox = CheckBox("启用 CurseForge（测试版）", options_card)
        server_second_pass_checkbox = CheckBox("启用 2 次筛选补查", options_card)
        for checkbox in (
            server_use_mcmod_checkbox,
            server_use_cf_checkbox,
            server_second_pass_checkbox,
        ):
            options_layout.addWidget(checkbox)

        server_start_button = PrimaryPushButton("开始制作服务端", options_card)
        server_start_button.clicked.connect(self.app.start_server_task)
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
            apply_label_tone(label, muted=True)
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
        server_stage_label.setStyleSheet(f"color: {TEXT_COLOR}; background: transparent;")
        status_layout.addWidget(server_stage_label)

        server_status_label = BodyLabel("请选择客户端输入源和输出目录，然后开始制作服务端。", status_card)
        server_status_label.setWordWrap(True)
        apply_label_tone(server_status_label, muted=True)
        status_layout.addWidget(server_status_label)

        server_progress_bar = ProgressBar(status_card)
        server_progress_bar.setRange(0, 100)
        server_progress_bar.setValue(0)
        status_layout.addWidget(server_progress_bar)

        server_download_label = BodyLabel(build_idle_download_status_text(), status_card)
        server_download_label.setWordWrap(True)
        apply_label_tone(server_download_label, muted=True)
        status_layout.addWidget(server_download_label)

        server_output_label = BodyLabel("输出位置：尚未运行", status_card)
        server_output_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        server_output_label.setWordWrap(True)
        apply_label_tone(server_output_label, muted=True)
        status_layout.addWidget(server_output_label)

        server_action_row = QHBoxLayout()
        server_result_button = PushButton("打开服务端目录", status_card)
        server_result_button.setEnabled(False)
        server_result_button.clicked.connect(lambda: self.app.open_panel_path("server", "result"))
        server_action_row.addWidget(server_result_button)

        server_extra_button = PushButton("打开日志目录", status_card)
        server_extra_button.setEnabled(False)
        server_extra_button.clicked.connect(lambda: self.app.open_panel_path("server", "extra"))
        server_action_row.addWidget(server_extra_button)

        server_report_button = PushButton("查看结果报告", status_card)
        server_report_button.clicked.connect(lambda: self.app.open_page(self.app.report_page))
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
        apply_read_only_editor_style(server_summary_edit)
        summary_layout.addWidget(server_summary_edit)

        log_page = QWidget(preview_card)
        log_layout = QVBoxLayout(log_page)
        log_layout.setContentsMargins(0, 0, 0, 0)
        server_log_edit = PlainTextEdit(log_page)
        server_log_edit.setReadOnly(True)
        server_log_edit.setPlainText("实时日志会滚动显示在这里。")
        apply_read_only_editor_style(server_log_edit, console=True)
        log_layout.addWidget(server_log_edit)

        tab_host, _, _ = build_tab_host(
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

        return ServerPageBuild(
            page=page,
            panel=TaskPanelState(
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
            inputs=ServerInputWidgets(
                client_path_edit=server_client_path_edit,
                output_path_edit=server_output_path_edit,
                download_source_combo=server_download_source_combo,
                use_mcmod_checkbox=server_use_mcmod_checkbox,
                use_cf_checkbox=server_use_cf_checkbox,
                second_pass_checkbox=server_second_pass_checkbox,
            ),
        )

    def build_report_page(self) -> ReportPageBuild:
        page = ScrollablePage(
            "reportPage",
            "结果报告",
            "这里专门负责回看最近一次筛模组和最近一次开服结果，少走目录、少翻日志。",
            self.app,
        )
        dashboard = QWidget(page)
        dashboard_layout = QGridLayout(dashboard)
        dashboard_layout.setContentsMargins(0, 0, 0, 0)
        dashboard_layout.setHorizontalSpacing(16)
        dashboard_layout.setVerticalSpacing(16)
        dashboard_layout.setColumnStretch(0, 1)
        dashboard_layout.setColumnStretch(1, 1)

        mod_card, mod_layout = self._create_card("模组筛选结果", "用来快速打开最近一次分类结果目录。")
        mod_status = StrongBodyLabel("当前还没有模组筛选结果。", mod_card)
        mod_status.setStyleSheet(f"color: {TEXT_COLOR}; background: transparent;")
        mod_layout.addWidget(mod_status)
        mod_summary = PlainTextEdit(mod_card)
        mod_summary.setReadOnly(True)
        mod_summary.setMinimumHeight(220)
        mod_summary.setPlainText("完成一次模组筛选后，这里会同步结果摘要。")
        apply_read_only_editor_style(mod_summary)
        mod_layout.addWidget(mod_summary)

        mod_button_row = QHBoxLayout()
        mod_result_button = PushButton("打开结果目录", mod_card)
        mod_result_button.setEnabled(False)
        mod_result_button.clicked.connect(lambda: self.app.open_report_path("mod", "result"))
        mod_button_row.addWidget(mod_result_button)
        mod_page_button = PushButton("回到模组筛选页", mod_card)
        mod_page_button.clicked.connect(lambda: self.app.open_page(self.app.mod_page))
        mod_button_row.addWidget(mod_page_button)
        mod_button_row.addStretch(1)
        mod_layout.addLayout(mod_button_row)

        server_card, server_layout = self._create_card("一键开服结果", "用来快速打开最近一次服务端目录和日志目录。")
        server_status = StrongBodyLabel("当前还没有服务端制作结果。", server_card)
        server_status.setStyleSheet(f"color: {TEXT_COLOR}; background: transparent;")
        server_layout.addWidget(server_status)
        server_summary = PlainTextEdit(server_card)
        server_summary.setReadOnly(True)
        server_summary.setMinimumHeight(220)
        server_summary.setPlainText("完成一次服务端制作后，这里会同步服务端目录、日志目录和启动脚本位置。")
        apply_read_only_editor_style(server_summary)
        server_layout.addWidget(server_summary)

        server_button_row = QHBoxLayout()
        server_result_button = PushButton("打开服务端目录", server_card)
        server_result_button.setEnabled(False)
        server_result_button.clicked.connect(lambda: self.app.open_report_path("server", "result"))
        server_button_row.addWidget(server_result_button)

        server_extra_button = PushButton("打开日志目录", server_card)
        server_extra_button.setEnabled(False)
        server_extra_button.clicked.connect(lambda: self.app.open_report_path("server", "extra"))
        server_button_row.addWidget(server_extra_button)
        server_page_button = PushButton("回到一键开服页", server_card)
        server_page_button.clicked.connect(lambda: self.app.open_page(self.app.server_page))
        server_button_row.addWidget(server_page_button)
        server_button_row.addStretch(1)
        server_layout.addLayout(server_button_row)

        usage_card, usage_layout = self._create_card(
            "怎么看这些结果",
            "报告页不负责跑任务，它只负责集中给你开目录和回看摘要。",
            variant="hero",
        )
        for text in [
            "筛模组完成后，优先从模组筛选页右侧的结果预览看待确认项。",
            "一键开服完成后，服务端目录和日志目录都能从这里直接打开。",
            "如果想继续操作，右侧按钮可以直接跳回对应工作页。",
        ]:
            label = BodyLabel(f"• {text}", usage_card)
            label.setWordWrap(True)
            apply_label_tone(label, muted=True)
            usage_layout.addWidget(label)

        dashboard_layout.addWidget(mod_card, 0, 0)
        dashboard_layout.addWidget(server_card, 0, 1)
        dashboard_layout.addWidget(usage_card, 1, 0, 1, 2)

        page.container_layout.addWidget(dashboard)
        page.container_layout.addStretch(1)

        return ReportPageBuild(
            page=page,
            sections={
                "mod": ReportSectionState(
                    status_label=mod_status,
                    summary_edit=mod_summary,
                    result_button=mod_result_button,
                    extra_button=None,
                ),
                "server": ReportSectionState(
                    status_label=server_status,
                    summary_edit=server_summary,
                    result_button=server_result_button,
                    extra_button=server_extra_button,
                ),
            },
        )

    def build_settings_page(self) -> ScrollablePage:
        page = ScrollablePage(
            "settingsPage",
            "设置",
            "这一页先放技术栈、缓存清理和当前界面目标，后面再把更细的偏好配置补进来。",
            self.app,
        )

        dashboard = QWidget(page)
        dashboard_layout = QGridLayout(dashboard)
        dashboard_layout.setContentsMargins(0, 0, 0, 0)
        dashboard_layout.setHorizontalSpacing(16)
        dashboard_layout.setVerticalSpacing(16)
        dashboard_layout.setColumnStretch(0, 1)
        dashboard_layout.setColumnStretch(1, 1)

        stack_card, stack_layout = self._create_card("当前界面技术栈", variant="hero")
        for text in [
            f"桌面框架：PySide6 {getattr(sys.modules.get('PySide6'), '__version__', '')}".strip(),
            f"Fluent 组件：qfluentwidgets {qfluentwidgets.__version__}",
            "设计方向：深色 Fluent 工具台，优先突出运行状态、下载状态、日志和结果目录。",
        ]:
            label = BodyLabel(text, stack_card)
            label.setWordWrap(True)
            apply_label_tone(label, muted=True)
            stack_layout.addWidget(label)

        support_card, support_layout = self._create_card("输入与缓存")
        for text in [
            "支持目录、mrpack、zip 直接导入。",
            "支持拖放文件夹和整合包到窗口中。",
            "整合包缓存和浏览器缓存会在启动与退出时做一次清理。",
        ]:
            label = BodyLabel(f"• {text}", support_card)
            label.setWordWrap(True)
            apply_label_tone(label, muted=True)
            support_layout.addWidget(label)

        cleanup_button = PrimaryPushButton("立即清理整合包缓存", support_card)
        cleanup_button.clicked.connect(self.app.cleanup_import_cache)
        support_layout.addWidget(cleanup_button, 0, Qt.AlignLeft)

        direction_card, direction_layout = self._create_card("界面目标")
        for text in [
            "信息尽量首屏可见，避免用户为了看状态来回滚动。",
            "操作入口固定在左侧，运行反馈固定在右侧，减轻任务时的视线跳转。",
            "动画只做轻反馈，不做花里胡哨的抢注意力效果。",
        ]:
            label = BodyLabel(f"• {text}", direction_card)
            label.setWordWrap(True)
            apply_label_tone(label, muted=True)
            direction_layout.addWidget(label)

        dashboard_layout.addWidget(stack_card, 0, 0)
        dashboard_layout.addWidget(support_card, 0, 1)
        dashboard_layout.addWidget(direction_card, 1, 0, 1, 2)

        page.container_layout.addWidget(dashboard)
        page.container_layout.addStretch(1)
        return page
