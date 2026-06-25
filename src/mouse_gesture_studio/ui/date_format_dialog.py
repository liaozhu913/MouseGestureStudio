from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)


WEEKDAYS_CN = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
WEEKDAYS_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
WEEKDAYS_EN_SHORT = ["Mon.", "Tue.", "Wed.", "Thu.", "Fri.", "Sat.", "Sun."]


@dataclass(frozen=True)
class DateFormatOption:
    label: str
    value: str


def default_date_options(now: datetime | None = None) -> list[DateFormatOption]:
    current = now or datetime.now()
    date_dash = current.strftime("%Y-%m-%d")
    date_dot = current.strftime("%Y.%m.%d")
    date_slash = current.strftime("%Y/%m/%d")
    date_short = current.strftime("%y%m%d")
    time_hm = current.strftime("%H:%M")
    time_hms = current.strftime("%H:%M:%S")
    weekday_cn = WEEKDAYS_CN[current.weekday()]
    weekday_en = WEEKDAYS_EN[current.weekday()]
    weekday_en_short = WEEKDAYS_EN_SHORT[current.weekday()]
    day_of_year = current.timetuple().tm_yday
    cn_date = current.strftime("%Y年%m月%d日")

    values = [
        date_dash,
        date_dot,
        date_slash,
        date_short,
        f"liaozhu913-{current.strftime('%y%m%d-%H%M%S')}",
        f"liaozhu913-xwlb-{current.strftime('%y%m%d')}",
        f"liaozhu913-ksfx-{current.strftime('%y%m%d-%H%M%S')}",
        cn_date,
        f"{cn_date}{weekday_cn[-1]}",
        f"{cn_date} {weekday_cn} 今年第{day_of_year}天",
        f"{cn_date} 早安问候图，早上好语录图片，早安问候祝福语图片大全 {weekday_cn} 今年第{day_of_year}天",
        f"{cn_date} 精选{weekday_cn}早安祝福语，{weekday_cn}早上问候动态图",
        f"Alapi · 早报60s {current.strftime('%y-%m-%d')} {weekday_en}",
        current.strftime("%B"),
        current.strftime("%b."),
        f"{cn_date}{time_hm}",
        f"{date_dash} {time_hms}",
        f"{date_slash} {time_hms}",
        time_hm,
        time_hms,
        weekday_cn,
    ]
    return [DateFormatOption(label=f"{index} {value}", value=value) for index, value in enumerate(values, 1)]


class DateFormatDialog(QDialog):
    def __init__(
        self,
        options: list[DateFormatOption] | None = None,
        parent=None,
        title: str = "请选择格式",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(520, 560)
        self.setMinimumSize(420, 360)
        self._selected_value = ""

        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(False)
        self.list_widget.setStyleSheet(
            """
            QListWidget {
                background: white;
                border: 1px solid #D7DFEA;
                border-radius: 6px;
                padding: 6px 8px;
                font-size: 14px;
            }
            QListWidget::item {
                min-height: 28px;
                padding: 2px 6px;
            }
            QListWidget::item:selected {
                background: #DDEBFF;
                color: #10233D;
            }
            """
        )

        for option in options or default_date_options():
            item = QListWidgetItem(option.label)
            item.setData(Qt.ItemDataRole.UserRole, option.value)
            self.list_widget.addItem(item)
        if self.list_widget.count():
            self.list_widget.setCurrentRow(0)
        self.list_widget.itemDoubleClicked.connect(self.accept)

        self.ok_button = QPushButton("确定(S)")
        self.cancel_button = QPushButton("取消(C)")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        button_row.addWidget(self.ok_button)
        button_row.addWidget(self.cancel_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(10)
        layout.addWidget(self.list_widget, stretch=1)
        layout.addLayout(button_row)

    def accept(self) -> None:
        item = self.list_widget.currentItem()
        if item:
            self._selected_value = str(item.data(Qt.ItemDataRole.UserRole))
        super().accept()

    def selected_value(self) -> str:
        return self._selected_value
