# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

寸止计时器 — 基于 Python tkinter 的桌面计时工具，用于记录"寸止"（Edging）训练 session 的主计时和每次寸止的独立时长。

## 运行

```bash
python edging_timer.py
```

无需安装第三方库，仅依赖 Python 标准库（tkinter）。要求 Python 3.6+。

## 架构

单文件应用，整个项目只有一个 `edging_timer.py`（488 行），包含一个核心类 `EdgingTimer`。

### 状态机

应用通过 `self.state` 驱动的状态机控制所有交互：

```
IDLE → RUNNING → EDGING → RUNNING (循环)
                ↘ PAUSED → RUNNING
```

- **idle**: 初始状态，等待点击"开始"
- **running**: 主计时运行中，寸止按钮可用
- **edging**: 寸止模式，寸止计时独立运行
- **paused**: 主计时暂停，寸止按钮禁用

所有状态转换和副作用集中在对应的事件方法中（`_on_start`, `_on_pause`, `_on_edge`, `_on_reset`）。

### 计时循环

通过 `tkinter.after(1000, self._tick)` 实现每秒回调，不依赖 `time.sleep()`。每次 tick 叠加 `self.total_seconds` 和 `self.edge_seconds`（仅在 edging 状态），然后调用 `_update_display()` 刷新 UI。`_cancel_tick()` 通过保存的 `self._job` ID 取消定时器实现暂停和重置。

### UI 布局

使用 tkinter `pack()` 布局，从上到下：标题 → 主计时大数字 → 寸止信息行 → 寸止按钮（核心交互）→ 控制按钮行（开始/暂停/重置）→ 寸止记录文本框。暗色主题，配色定义在 `_build_ui()` 顶部常量 `bg`, `fg`, `accent`。

### 数据记录

`self.edge_records` 是 `list[int]`，存储每次寸止的秒数。文本框为只读（`state=tk.DISABLED`），写入时临时切换到 NORMAL 再切回。

## 代码风格

- Python 源码用中文注释，注释量大（约 40% 内容为注释），每行源码几乎都有对应的解释
- 类和方法有详细的 docstring
- 注释使用 80 字符宽度对齐
