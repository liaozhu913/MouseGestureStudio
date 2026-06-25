# PDCA 执行记录

## Plan

- 目标：在 Windows 上落地一个可常驻运行的鼠标手势工具。
- 约束：具备图形化配置界面、可自定义手势、支持复制/粘贴/前进/后退/发送快捷键等核心能力。
- 技术选型：`Python 3.12 + PySide6 + ctypes Win32 API + PyInstaller`。

## Do

- 搭建项目目录与独立虚拟环境，避免长路径安装问题。
- 实现手势模板配置、默认动作、图形界面、轨迹重绘、托盘常驻。
- 实现 Windows 全局鼠标低级钩子与 `SendInput` 动作执行。

## Check

- 使用源码直接运行进行 GUI 与识别逻辑验证。
- 使用脚本做识别器和配置层的基础自检。
- 使用 `PyInstaller` 生成 `dist` 版本做打包验证。

### 本轮验证结果

- `compileall` 通过，源码可编译。
- 主窗口、动作编辑窗口、重绘轨迹窗口均已完成烟测。
- `scripts/smoke_test.py` 通过，默认手势可正确匹配自身模板。
- 打包产物 `D:\MouseGestureStudio\dist\MouseGestureStudio\MouseGestureStudio.exe` 已验证可启动。

## Act

- 后续可扩展：
- 排除应用名单
- 更丰富的动作类型
- 手势冲突检测
- 导入/导出配置
