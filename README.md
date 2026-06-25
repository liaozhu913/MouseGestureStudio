# MouseGestureStudio

一个面向 Windows 的鼠标手势小工具，参考你提供的界面风格与交互方式实现，支持：

- 全局鼠标手势识别
- 图形化手势管理界面
- 自定义手势轨迹
- 常用动作：复制、粘贴、前进、后退、撤销、重做、全选等
- 自定义发送快捷键
- 自定义动作触发后的延迟时间
- 输入文本、打开文件/网址/命令
- 托盘常驻运行
- 打包为独立 `exe`
- 生成 Windows 安装包

## 运行

```powershell
D:\MouseGestureStudio\.venv\Scripts\python.exe -m pip install -r D:\MouseGestureStudio\requirements.txt
D:\MouseGestureStudio\.venv\Scripts\python.exe D:\MouseGestureStudio\src\mouse_gesture_studio\main.py
```

## 打包

```powershell
powershell -ExecutionPolicy Bypass -File D:\MouseGestureStudio\scripts\build.ps1
```

输出目录：

- `D:\MouseGestureStudio\dist\MouseGestureStudio`

## 生成安装包

```powershell
powershell -ExecutionPolicy Bypass -File D:\MouseGestureStudio\scripts\package-installer.ps1
```

输出文件：

- `D:\MouseGestureStudio\artifacts\MouseGestureStudio-Setup-0.2.0.exe`

安装器为当前用户安装到 `%LocalAppData%\Programs\MouseGestureStudio`，并创建开始菜单、桌面快捷方式和“应用和功能”卸载项。升级安装时会保留已安装目录中的 `data\settings.json`。

用户手势配置统一保存到：

- `%APPDATA%\MouseGestureStudio\settings.json`

首次启动新版时会自动从旧版运行目录中的 `data\settings.json` 迁移最近修改的一份配置，避免开发版、免安装版和安装版读到不同手势。

## 默认操作方式

- 默认触发键：`鼠标右键`
- 按住触发键并移动鼠标绘制手势
- 松开后执行匹配动作
- 如果几乎没有移动，则自动补发普通右键点击，不影响正常右键菜单

## 项目结构

- `src\mouse_gesture_studio\` 应用源码
- `docs\PDCA.md` 按 PDCA 记录的实施过程
- `scripts\run.ps1` 开发启动脚本
- `scripts\build.ps1` 打包脚本
- `scripts\package-installer.ps1` 安装包生成脚本
