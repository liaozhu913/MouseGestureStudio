from __future__ import annotations

from typing import Iterable

from .models import ActionConfig, AppSettings, GestureTemplate


BUILTIN_ACTIONS: list[dict[str, str]] = [
    {"id": "copy", "name": "复制"},
    {"id": "paste", "name": "粘贴"},
    {"id": "cut", "name": "剪切"},
    {"id": "undo", "name": "撤销"},
    {"id": "redo", "name": "重做"},
    {"id": "select_all", "name": "全选"},
    {"id": "browser_back", "name": "浏览器后退"},
    {"id": "browser_forward", "name": "浏览器前进"},
    {"id": "close_tab", "name": "关闭标签页"},
    {"id": "reopen_tab", "name": "恢复关闭标签页"},
    {"id": "new_tab", "name": "新建标签页"},
    {"id": "close_window", "name": "关闭窗口"},
    {"id": "show_desktop", "name": "显示桌面"},
    {"id": "task_view", "name": "任务视图"},
    {"id": "snip", "name": "截图工具"},
]


TRIGGER_BUTTONS = [
    ("right", "鼠标右键"),
    ("middle", "鼠标中键"),
    ("x1", "鼠标侧键 X1"),
    ("x2", "鼠标侧键 X2"),
]


ACTION_KINDS = [
    ("builtin", "常用功能(快捷操作)"),
    ("shortcut", "发送快捷键"),
    ("text", "输入纯文本"),
    ("launch", "打开或运行(文件/目录/命令/网址等)"),
    ("workflow", "组合动作(原生步骤流)"),
]


WORKFLOW_DATE_PICKER = """{
  "name": "选择日期格式并写入",
  "description": "弹出日期格式选择框，选择后自动粘贴到当前输入框。",
  "vars": {},
  "steps": [
    {
      "kind": "date_picker",
      "paste": true,
      "formats": [
        "{date}",
        "{date_dot}",
        "{date_slash}",
        "{date_short}",
        "liaozhu913-{date_short}-{time_short}",
        "liaozhu913-xwlb-{date_short}",
        "liaozhu913-ksfx-{date_short}-{time_short}",
        "{date_cn}",
        "{date_cn} {time_short}",
        "早报-{date_cn}-{time_short}",
        "{date_cn} 精选早安祝福语，星期问候动态图"
      ]
    }
  ]
}"""


WORKFLOW_CHOICE_DAILY_DATE = """{
  "name": "选择日报日期并写入",
  "description": "弹出通用选择框，让用户选择一种日期文本，然后自动粘贴到当前输入框。",
  "vars": {},
  "steps": [
    {
      "kind": "choice",
      "title": "请选择日报日期格式",
      "var": "picked_date",
      "clipboard": true,
      "paste": true,
      "options": [
        {
          "label": "早报短日期",
          "value": "早报-{date_short}"
        },
        {
          "label": "中文日期",
          "value": "{date_cn}"
        },
        {
          "label": "中文日期 + 时间",
          "value": "{date_cn} {time_short}"
        },
        {
          "label": "日报固定标题",
          "value": "{date_cn} 早报时间更新"
        }
      ]
    }
  ]
}"""


WORKFLOW_OPEN_DAILY_WEBSITES = """{
  "name": "打开每日固定网页",
  "description": "一次性打开每天需要看的几个网页。",
  "vars": {},
  "steps": [
    {
      "kind": "open_urls",
      "interval_ms": 250,
      "urls": [
        "https://www.bing.com",
        "https://news.ycombinator.com",
        "https://www.getquicker.net"
      ]
    }
  ]
}"""


WORKFLOW_OPEN_SELECTED_URLS = """{
  "name": "打开选中的多行网址",
  "description": "先复制当前选中的文本，再自动提取里面的网址；会过滤空行、空格、说明文字和尾随标点，单个网址失败不会中断后续打开。",
  "vars": {},
  "steps": [
    {
      "kind": "get_selected_text",
      "var": "selected_text",
      "delay_ms": 150
    },
    {
      "kind": "open_urls",
      "urls": "{selected_text}",
      "interval_ms": 250
    }
  ]
}"""


def points_from_vertices(
    vertices: Iterable[tuple[float, float]],
    density: int = 12,
) -> list[tuple[float, float]]:
    items = list(vertices)
    if len(items) < 2:
        return items

    result: list[tuple[float, float]] = []
    for start, end in zip(items, items[1:]):
        sx, sy = start
        ex, ey = end
        for index in range(density):
            t = index / density
            result.append((sx + (ex - sx) * t, sy + (ey - sy) * t))
    result.append(items[-1])
    return result


def build_default_settings() -> AppSettings:
    gestures = [
        GestureTemplate(
            id="gesture-left",
            name="浏览器后退",
            points=points_from_vertices([(0.85, 0.5), (0.15, 0.5)]),
            action=ActionConfig(kind="builtin", builtin_name="browser_back"),
            hint="后退",
        ),
        GestureTemplate(
            id="gesture-right",
            name="浏览器前进",
            points=points_from_vertices([(0.15, 0.5), (0.85, 0.5)]),
            action=ActionConfig(kind="builtin", builtin_name="browser_forward"),
            hint="前进",
        ),
        GestureTemplate(
            id="gesture-up",
            name="复制",
            points=points_from_vertices([(0.5, 0.85), (0.5, 0.15)]),
            action=ActionConfig(kind="builtin", builtin_name="copy"),
            hint="复制",
        ),
        GestureTemplate(
            id="gesture-down",
            name="粘贴",
            points=points_from_vertices([(0.5, 0.15), (0.5, 0.85)]),
            action=ActionConfig(kind="builtin", builtin_name="paste"),
            hint="粘贴",
        ),
        GestureTemplate(
            id="gesture-down-left",
            name="截图",
            points=points_from_vertices([(0.8, 0.2), (0.2, 0.8)]),
            action=ActionConfig(kind="builtin", builtin_name="snip"),
            hint="截图",
        ),
        GestureTemplate(
            id="gesture-hook",
            name="撤销",
            points=points_from_vertices(
                [(0.7, 0.2), (0.55, 0.85), (0.4, 0.8), (0.35, 0.55)]
            ),
            action=ActionConfig(kind="builtin", builtin_name="undo"),
            hint="撤销",
        ),
        GestureTemplate(
            id="gesture-arch",
            name="全选",
            points=points_from_vertices(
                [(0.15, 0.75), (0.25, 0.35), (0.5, 0.2), (0.75, 0.35), (0.85, 0.75)]
            ),
            action=ActionConfig(kind="builtin", builtin_name="select_all"),
            hint="全选",
        ),
        GestureTemplate(
            id="gesture-s",
            name="恢复关闭标签页",
            points=points_from_vertices(
                [(0.8, 0.2), (0.4, 0.15), (0.2, 0.35), (0.6, 0.55), (0.8, 0.75), (0.3, 0.8)]
            ),
            action=ActionConfig(kind="builtin", builtin_name="reopen_tab"),
            hint="恢复标签页",
        ),
        GestureTemplate(
            id="gesture-insert-datetime",
            name="选择日期格式",
            points=points_from_vertices([(0.2, 0.2), (0.8, 0.2), (0.8, 0.8)]),
            action=ActionConfig(
                kind="workflow",
                workflow=WORKFLOW_DATE_PICKER,
            ),
            hint="选择日期格式",
        ),
        GestureTemplate(
            id="gesture-choice-daily-date",
            name="日报日期选择器",
            points=points_from_vertices([(0.2, 0.8), (0.5, 0.2), (0.8, 0.8), (0.35, 0.45)]),
            action=ActionConfig(kind="workflow", workflow=WORKFLOW_CHOICE_DAILY_DATE),
            hint="选择日报日期",
        ),
        GestureTemplate(
            id="gesture-open-daily-sites",
            name="打开每日网页",
            points=points_from_vertices([(0.2, 0.25), (0.8, 0.25), (0.2, 0.75), (0.8, 0.75)]),
            action=ActionConfig(kind="workflow", workflow=WORKFLOW_OPEN_DAILY_WEBSITES),
            hint="打开每日网页",
        ),
        GestureTemplate(
            id="gesture-open-selected-urls",
            name="打开选中网址",
            points=points_from_vertices([(0.25, 0.2), (0.75, 0.2), (0.75, 0.5), (0.25, 0.5), (0.25, 0.8), (0.75, 0.8)]),
            action=ActionConfig(kind="workflow", workflow=WORKFLOW_OPEN_SELECTED_URLS),
            hint="提取并打开网址",
        ),
    ]
    return AppSettings(gestures=gestures)


def builtin_name(action_id: str) -> str:
    for action in BUILTIN_ACTIONS:
        if action["id"] == action_id:
            return action["name"]
    return action_id
