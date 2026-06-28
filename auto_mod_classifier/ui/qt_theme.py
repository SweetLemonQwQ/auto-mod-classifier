from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QWidget
from qfluentwidgets import BodyLabel, PlainTextEdit, StrongBodyLabel


PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_ICON_PATH = PROJECT_ROOT / "自动筛选模组分类器.ico"

BG_COLOR = "#0F172A"
SURFACE_COLOR = "#1B2336"
SURFACE_ALT_COLOR = "#111827"
SURFACE_HERO_COLOR = "#15263A"
BORDER_COLOR = "#334155"
TEXT_COLOR = "#F8FAFC"
MUTED_TEXT_COLOR = "#94A3B8"
ACCENT_COLOR = "#22C55E"
ACCENT_SOFT_COLOR = "#163123"
IDLE_COLOR = "#64748B"
RUNNING_COLOR = "#38BDF8"
SUCCESS_COLOR = "#22C55E"
WARNING_COLOR = "#F59E0B"
ERROR_COLOR = "#EF4444"


def build_window_stylesheet() -> str:
    """主窗口统一样式。"""

    return f"""
    QLabel {{
        color: {TEXT_COLOR};
        background: transparent;
    }}
    BodyLabel, StrongBodyLabel, TitleLabel, SubtitleLabel {{
        color: {TEXT_COLOR};
        background: transparent;
    }}
    QCheckBox {{
        color: {TEXT_COLOR};
        background: transparent;
        spacing: 8px;
    }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
    }}
    QPushButton {{
        min-height: 32px;
    }}
    QHeaderView::section {{
        background-color: {SURFACE_ALT_COLOR};
        color: {TEXT_COLOR};
        border: 0;
        border-bottom: 1px solid {BORDER_COLOR};
        padding: 6px 8px;
    }}
    QTableCornerButton::section {{
        background-color: {SURFACE_ALT_COLOR};
        border: 0;
        border-right: 1px solid {BORDER_COLOR};
        border-bottom: 1px solid {BORDER_COLOR};
    }}
    QProgressBar {{
        min-height: 12px;
        background-color: {SURFACE_ALT_COLOR};
        color: {TEXT_COLOR};
        border: 1px solid {BORDER_COLOR};
        border-radius: 7px;
        text-align: center;
    }}
    QProgressBar::chunk {{
        background-color: {ACCENT_COLOR};
        border-radius: 6px;
    }}
    """


def install_shadow(widget: QWidget, *, blur_radius: int = 18, y_offset: int = 7) -> None:
    """给卡片一层轻阴影，提升一点桌面工具的质感。"""

    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur_radius)
    effect.setOffset(0, y_offset)
    effect.setColor(QColor(3, 7, 18, 90))
    widget.setGraphicsEffect(effect)


def apply_card_style(widget: QWidget, variant: str = "panel") -> None:
    if variant == "metric":
        background = SURFACE_ALT_COLOR
        border = BORDER_COLOR
    elif variant == "hero":
        background = SURFACE_HERO_COLOR
        border = "#3B5169"
    elif variant == "soft":
        background = ACCENT_SOFT_COLOR
        border = "#256D3D"
    else:
        background = SURFACE_COLOR
        border = BORDER_COLOR

    object_name = f"{variant}Card"
    widget.setObjectName(object_name)
    widget.setStyleSheet(
        f"""
        QWidget#{object_name} {{
            background-color: {background};
            border: 1px solid {border};
            border-radius: 8px;
        }}
        """
    )
    install_shadow(widget)


def apply_read_only_editor_style(editor: PlainTextEdit, *, console: bool = False) -> None:
    background = "#0B1220" if console else SURFACE_ALT_COLOR
    font_family = "Consolas, Microsoft YaHei UI" if console else "Microsoft YaHei UI"
    editor.setStyleSheet(
        f"""
        background-color: {background};
        color: {TEXT_COLOR};
        border: 1px solid {BORDER_COLOR};
        border-radius: 8px;
        selection-background-color: {ACCENT_COLOR};
        font-family: {font_family};
        font-size: 12px;
        """
    )


def apply_input_style(widget: QWidget) -> None:
    widget.setStyleSheet(
        f"""
        background-color: {SURFACE_ALT_COLOR};
        color: {TEXT_COLOR};
        border: 1px solid {BORDER_COLOR};
        border-radius: 8px;
        padding: 0 12px;
        min-height: 32px;
        """
    )


def apply_label_tone(label: QWidget | BodyLabel | StrongBodyLabel, *, muted: bool = False) -> None:
    color = MUTED_TEXT_COLOR if muted else TEXT_COLOR
    label.setStyleSheet(f"color: {color}; background: transparent;")
