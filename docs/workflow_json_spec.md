# MouseGestureStudio 组合动作 JSON 规则

MouseGestureStudio 可以作为一个“动作运行壳”：用户把符合本规则的 JSON 粘贴到手势的“组合动作”步骤框里，或导入 `.json` 文件，即可通过鼠标手势执行一组自动化动作。

## 顶层结构

推荐使用对象结构：

```json
{
  "name": "动作名称",
  "description": "给用户看的说明，可选",
  "vars": {
    "变量名": "变量值"
  },
  "steps": [
    {"kind": "clipboard", "value": "Hello"},
    {"kind": "paste"}
  ]
}
```

也支持直接写步骤数组：

```json
[
  {"kind": "clipboard", "value": "Hello"},
  {"kind": "paste"}
]
```

## 模板变量

大多数字段支持 `{变量名}` 替换。

内置变量：

- `{date}`: `2026-06-25`
- `{date_dot}`: `2026.06.25`
- `{date_slash}`: `2026/06/25`
- `{date_short}`: `260625`
- `{date_cn}`: `2026年06月25日`
- `{time}`: `03:17:21`
- `{time_short}`: `03:17`
- `{datetime}`: `2026-06-25 03:17:21`
- `{clipboard}`: 当前剪贴板文本

运行中产生的变量：

- `get_selected_text` 默认写入 `{selected_text}`
- `date_picker` 默认写入 `{selected}`
- `choice` 默认写入 `{selected}`
- `foreach_line` 默认写入 `{item}` 和 `{index}`

## 步骤类型

### `date_picker`

弹出日期格式选择框，用户选择后写入变量，可选自动复制到剪贴板并粘贴。

```json
{"kind": "date_picker", "paste": true}
```

自定义格式：

```json
{
  "kind": "date_picker",
  "paste": true,
  "formats": [
    "{date}",
    "{date_dot}",
    "{date_cn} {time_short}",
    "早报-{date_short}-{time_short}"
  ]
}
```

### `clipboard`

设置剪贴板文本。

```json
{"kind": "clipboard", "value": "{date_cn} {time}"}
```

### `choice`

弹出通用选择框，用户选择一个选项后写入变量。它适合做自定义菜单，例如选择日报日期格式、选择常用话术、选择环境地址。

```json
{
  "kind": "choice",
  "title": "请选择日报日期格式",
  "var": "picked_date",
  "clipboard": true,
  "paste": true,
  "options": [
    {"label": "日报标题", "value": "早报-{date_short}"},
    {"label": "中文日期", "value": "{date_cn}"},
    {"label": "日期加时间", "value": "{date_cn} {time_short}"}
  ]
}
```

选择后继续执行后续步骤：

```json
{
  "kind": "choice",
  "title": "选择要打开的工作区",
  "var": "workspace",
  "options": [
    {"label": "生产环境", "value": "https://example.com/prod"},
    {"label": "测试环境", "value": "https://example.com/test"}
  ],
  "steps": [
    {"kind": "open_url", "url": "{workspace}"}
  ]
}
```

### `paste`

向当前焦点窗口发送 `Ctrl+V`。

```json
{"kind": "paste"}
```

### `text`

直接输入文本。

```json
{"kind": "text", "value": "你好，今天是 {date_cn}"}
```

### `shortcut`

发送快捷键。

```json
{"kind": "shortcut", "keys": "Ctrl+Shift+T"}
```

### `delay`

等待指定毫秒。

```json
{"kind": "delay", "ms": 300}
```

### `launch`

打开程序、文件、目录或命令。

```json
{"kind": "launch", "target": "notepad.exe"}
```

### `open_url`

打开一个网址。传入内容里可以夹带说明文字或尾随标点，工具会自动提取第一个可识别的网址并清洗后打开；如果打开失败，会跳过而不是中断整个动作。

```json
{"kind": "open_url", "url": "请打开：https://example.com。"}
```

### `open_urls`

批量打开网址。`urls` 可以是数组，也可以是一段混杂文本；工具会自动提取里面真正的网址，过滤空行、空格、普通文字、尾随标点，并按顺序去重打开。单个网址失败不会影响后续网址。

```json
{
  "kind": "open_urls",
  "interval_ms": 200,
  "urls": [
    "工作台：https://news.ycombinator.com",
    "搜索 www.bing.com；",
    "官网：https://www.getquicker.net"
  ]
}
```

### `get_selected_text`

复制当前选中文本到变量。默认变量名是 `selected_text`。

```json
{"kind": "get_selected_text", "var": "selected_text", "delay_ms": 120}
```

### `foreach_line`

逐行处理某个变量里的文本。

```json
{
  "kind": "foreach_line",
  "var": "selected_text",
  "as": "url",
  "steps": [
    {"kind": "open_url", "url": "{url}"},
    {"kind": "delay", "ms": 200}
  ]
}
```

### `set_var`

设置变量。

```json
{"kind": "set_var", "name": "title", "value": "日报-{date_short}"}
```

### `builtin`

调用内置快捷动作。

```json
{"kind": "builtin", "name": "copy"}
```

可用名称包括：`copy`、`paste`、`cut`、`undo`、`redo`、`select_all`、`browser_back`、`browser_forward`、`close_tab`、`reopen_tab`、`new_tab`、`close_window`、`show_desktop`、`task_view`、`snip`。

## 让 AI 生成动作 JSON 的提示词模板

把下面这段发给 AI，再补充你的具体需求；同样内容也保存为 `docs/ai_workflow_prompt_template.txt`，方便直接复制。

```text
请为 MouseGestureStudio 生成一个“组合动作 JSON”。

规则：
1. 只输出合法 JSON，不要 Markdown，不要解释文字。
2. 顶层使用对象结构：name、description、vars、steps。
3. steps 只能使用这些 kind：
   date_picker、choice、clipboard、paste、text、shortcut、delay、launch、open_url、open_urls、get_selected_text、foreach_line、set_var、builtin。
4. 字段里的变量可以使用：
   {date}、{date_dot}、{date_slash}、{date_short}、{date_cn}、{time}、{time_short}、{datetime}、{clipboard}。
5. 如果需要处理选中文本，先使用 get_selected_text。
6. 如果需要从选中文本里批量打开网址，使用 get_selected_text + open_urls；open_urls 会自动提取和清洗网址，不要用 foreach_line 逐行硬开。
7. 如果需要把内容写入当前输入框，优先使用 clipboard + paste，或 date_picker/choice 的 paste:true。
8. 不要生成未定义的 kind，不要生成注释，不要生成尾随逗号。

我的需求：
【在这里描述你想通过手势执行什么】
```

## 设计建议

- 面向输入框输出文本时，推荐 `clipboard` + `paste`，比逐字输入更稳定。
- 批量打开网页时，推荐给 `open_urls` 设置 `interval_ms`，避免浏览器短时间内收到太多打开请求。
- 处理用户选中的多行链接时，推荐 `get_selected_text` + `open_urls`，让工具自动从混杂文本里提取网址。
- 复杂动作先从 2-3 步开始测试，再逐步增加步骤。
