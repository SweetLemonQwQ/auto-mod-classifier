from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QWidget
from qfluentwidgets import BodyLabel, PlainTextEdit, StrongBodyLabel


PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_ICON_PATH = PROJECT_ROOT / "自动筛选模组分类器.ico"

BG_COLOR = "#0F172A"
SURFACE_COLOR = "#1E293B"
SURFACE_ALT_COLOR = "#334155"
SURFACE_HERO_COLOR = "#203049"
BORDER_COLOR = "#475569"
WEAK_BORDER_COLOR = "rgba(71, 85, 105, 76)"
TEXT_COLOR = "#F1F5F9"
SECONDARY_TEXT_COLOR = "#CBD5E1"
MUTED_TEXT_COLOR = "#94A3B8"
ACCENT_COLOR = "#34D399"
ACCENT_HOVER_COLOR = "#2CC98E"
ACCENT_PRESSED_COLOR = "#22B980"
ACCENT_DISABLED_COLOR = "rgba(52, 211, 153, 102)"
ACCENT_SOFT_COLOR = "rgba(52, 211, 153, 36)"
IDLE_COLOR = "#64748B"
RUNNING_COLOR = ACCENT_COLOR
SUCCESS_COLOR = "#22C55E"
WARNING_COLOR = "#F59E0B"
ERROR_COLOR = "#F87171"
INFO_COLOR = "#60A5FA"
WARNING_SOFT_COLOR = "rgba(245, 158, 11, 34)"
ERROR_SOFT_COLOR = "rgba(248, 113, 113, 34)"


def build_window_stylesheet() -> str:
    """主窗口统一样式。"""

    return f"""
    QWidget {{
        font-family: "Segoe UI", "Microsoft YaHei UI";
        font-size: 13px;
    }}
    QLabel {{
        color: {SECONDARY_TEXT_COLOR};
        background: transparent;
    }}
    BodyLabel, StrongBodyLabel, TitleLabel, SubtitleLabel {{
        background: transparent;
    }}
    BodyLabel {{
        color: {SECONDARY_TEXT_COLOR};
        font-size: 13px;
        font-weight: 400;
    }}
    StrongBodyLabel {{
        color: {TEXT_COLOR};
        font-size: 14px;
        font-weight: 600;
    }}
    TitleLabel {{
        color: {TEXT_COLOR};
        font-size: 20px;
        font-weight: 600;
    }}
    SubtitleLabel {{
        color: {SECONDARY_TEXT_COLOR};
        font-size: 14px;
        font-weight: 400;
    }}
    QCheckBox {{
        color: {SECONDARY_TEXT_COLOR};
        background: transparent;
        spacing: 8px;
    }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
    }}
    QPushButton {{
        min-height: 34px;
        max-height: 36px;
        padding: 0 20px;
        border-radius: 6px;
        border: 1px solid {WEAK_BORDER_COLOR};
        background-color: {SURFACE_ALT_COLOR};
        color: {TEXT_COLOR};
        font-size: 13px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        background-color: #3B4A60;
        border-color: rgba(148, 163, 184, 120);
    }}
    QPushButton:pressed {{
        background-color: #263548;
    }}
    QPushButton:disabled {{
        color: rgba(203, 213, 225, 90);
        background-color: rgba(51, 65, 85, 110);
        border-color: rgba(71, 85, 105, 60);
    }}
    PrimaryPushButton {{
        background-color: {ACCENT_COLOR};
        color: #052E22;
        border: 1px solid {ACCENT_COLOR};
    }}
    PrimaryPushButton:hover {{
        background-color: {ACCENT_HOVER_COLOR};
        border-color: {ACCENT_HOVER_COLOR};
    }}
    PrimaryPushButton:pressed {{
        background-color: {ACCENT_PRESSED_COLOR};
        border-color: {ACCENT_PRESSED_COLOR};
    }}
    PrimaryPushButton:disabled {{
        background-color: {ACCENT_DISABLED_COLOR};
        border-color: transparent;
        color: rgba(5, 46, 34, 125);
    }}
    QPushButton#smallButton {{
        min-height: 26px;
        max-height: 28px;
        padding: 0 12px;
        font-size: 12px;
    }}
    QPushButton#warningButton {{
        background-color: {WARNING_SOFT_COLOR};
        color: #FDBA74;
        border: 1px solid rgba(245, 158, 11, 120);
    }}
    QPushButton#warningButton:hover {{
        background-color: rgba(245, 158, 11, 54);
        border-color: rgba(245, 158, 11, 160);
    }}
    LineEdit, ComboBox, QLineEdit, QComboBox {{
        min-height: 32px;
        max-height: 32px;
        border-radius: 6px;
        border: 1px solid {WEAK_BORDER_COLOR};
        background-color: {SURFACE_ALT_COLOR};
        color: {TEXT_COLOR};
        padding: 0 12px;
        selection-background-color: {ACCENT_COLOR};
    }}
    QHeaderView::section {{
        background-color: #263548;
        color: {TEXT_COLOR};
        border: 0;
        border-bottom: 1px solid {WEAK_BORDER_COLOR};
        padding: 6px 8px;
        font-size: 12px;
        font-weight: 600;
    }}
    QTableCornerButton::section {{
        background-color: #263548;
        border: 0;
        border-right: 1px solid {WEAK_BORDER_COLOR};
        border-bottom: 1px solid {WEAK_BORDER_COLOR};
    }}
    QProgressBar {{
        min-height: 10px;
        max-height: 10px;
        background-color: #223046;
        color: {TEXT_COLOR};
        border: 0;
        border-radius: 5px;
        text-align: center;
    }}
    QProgressBar::chunk {{
        background-color: {ACCENT_COLOR};
        border-radius: 5px;
    }}
    QPlainTextEdit, QTextEdit {{
        background-color: #101827;
        color: {SECONDARY_TEXT_COLOR};
        border: 1px solid {WEAK_BORDER_COLOR};
        border-radius: 8px;
        selection-background-color: {ACCENT_COLOR};
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 4px 0 4px 0;
    }}
    QScrollBar::handle:vertical {{
        background: rgba(148, 163, 184, 95);
        border-radius: 4px;
        min-height: 36px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: rgba(148, 163, 184, 135);
    }}
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical,
    QScrollBar::add-page:vertical,
    QScrollBar::sub-page:vertical {{
        background: transparent;
        border: 0;
        height: 0;
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 8px;
        margin: 0 4px 0 4px;
    }}
    QScrollBar::handle:horizontal {{
        background: rgba(148, 163, 184, 95);
        border-radius: 4px;
        min-width: 36px;
    }}
    QScrollBar::add-line:horizontal,
    QScrollBar::sub-line:horizontal,
    QScrollBar::add-page:horizontal,
    QScrollBar::sub-page:horizontal {{
        background: transparent;
        border: 0;
        width: 0;
    }}
    """


def install_shadow(widget: QWidget, *, blur_radius: int = 14, y_offset: int = 3, alpha: int = 64) -> None:
    """给一级卡片加轻阴影，避免深色界面糊成一片。"""

    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur_radius)
    effect.setOffset(0, y_offset)
    effect.setColor(QColor(3, 7, 18, alpha))
    widget.setGraphicsEffect(effect)


def apply_card_style(widget: QWidget, variant: str = "panel") -> None:
    if variant == "metric":
        background = SURFACE_ALT_COLOR
        border = "transparent"
        shadow = False
    elif variant == "hero":
        background = SURFACE_HERO_COLOR
        border = WEAK_BORDER_COLOR
        shadow = True
    elif variant == "subtle":
        background = SURFACE_ALT_COLOR
        border = "transparent"
        shadow = False
    elif variant == "soft":
        background = ACCENT_SOFT_COLOR
        border = "rgba(52, 211, 153, 90)"
        shadow = False
    elif variant == "warning":
        background = WARNING_SOFT_COLOR
        border = "rgba(245, 158, 11, 95)"
        shadow = False
    else:
        background = SURFACE_COLOR
        border = WEAK_BORDER_COLOR
        shadow = True

    object_name = f"{variant}Card"
    widget.setObjectName(object_name)
    widget.setStyleSheet(
        f"""
        QWidget#{object_name} {{
            background-color: {background};
            border: 1px solid {border};
            border-radius: 8px;
        }}
        QWidget#{object_name}:hover {{
            border-color: rgba(148, 163, 184, 105);
        }}
        """
    )
    if shadow:
        install_shadow(widget)
    else:
        widget.setGraphicsEffect(None)


def apply_read_only_editor_style(editor: PlainTextEdit, *, console: bool = False) -> None:
    background = "#0B1220" if console else "#182235"
    font_family = "Consolas, Microsoft YaHei UI" if console else "Microsoft YaHei UI"
    editor.setStyleSheet(
        f"""
        background-color: {background};
        color: {SECONDARY_TEXT_COLOR};
        border: 1px solid {WEAK_BORDER_COLOR};
        border-radius: 8px;
        selection-background-color: {ACCENT_COLOR};
        font-family: {font_family};
        font-size: 12px;
        line-height: 18px;
        """
    )


def apply_input_style(widget: QWidget) -> None:
    widget.setStyleSheet(
        f"""
        background-color: {SURFACE_ALT_COLOR};
        color: {TEXT_COLOR};
        border: 1px solid {WEAK_BORDER_COLOR};
        border-radius: 6px;
        padding: 0 12px;
        min-height: 32px;
        max-height: 32px;
        """
    )


def apply_label_tone(
    label: QWidget | BodyLabel | StrongBodyLabel,
    *,
    muted: bool = False,
    level: int = 2,
    size: int | None = None,
    weight: int | None = None,
) -> None:
    if muted or level >= 3:
        color = MUTED_TEXT_COLOR
    elif level == 1:
        color = TEXT_COLOR
    else:
        color = SECONDARY_TEXT_COLOR
    extra = ""
    if size is not None:
        extra += f" font-size: {size}px;"
    if weight is not None:
        extra += f" font-weight: {weight};"
    label.setStyleSheet(f"color: {color}; background: transparent;")
    if extra:
        label.setStyleSheet(f"color: {color}; background: transparent;{extra}")
