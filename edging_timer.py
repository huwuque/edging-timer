#!/usr/bin/env python3
"""
寸止计时器 — 桌面手淫计时工具
=================================
功能说明：
  1. 主计时器 — 记录整个手淫 session 的总时长
  2. 寸止功能 — 快要射精时按下按钮，开始独立计时；
     忍耐期结束后再按一次，记录本次寸止时长并恢复到主计时
  3. 多次寸止记录 — 每次寸止的时长都会被记录下来
  4. 暂停/继续 — 可以随时暂停和恢复主计时
  5. 重置 — 清空所有数据回到初始状态

状态机：
  IDLE ──(开始)──> RUNNING ──(寸止)──> EDGING ──(停止寸止)──> RUNNING
    ^                  │                                         │
    └──(重置)──────────┴──(重置)─────────────────────────────────┘
                           RUNNING ──(暂停)──> PAUSED ──(继续)──> RUNNING
"""

import tkinter as tk       # Python 标准 GUI 库，用于构建桌面窗口
from tkinter import ttk     # tkinter 的主题组件（本次未使用，预留扩展）
# import time               # 未直接使用（通过 tkinter.after() 实现计时）


class EdgingTimer:
    """
    寸止计时器主类
    ===============
    封装了所有 UI 元素、计时逻辑、状态管理和事件处理。
    整个应用只有一个窗口，通过状态机来控制不同阶段的按钮行为。
    """

    def __init__(self):
        """初始化：创建窗口 → 设置状态变量 → 构建界面"""

        # ==================== 创建主窗口 ====================
        self.root = tk.Tk()                          # 创建 tkinter 根窗口
        self.root.title("寸止计时器")                  # 设置窗口标题
        self.root.geometry("420x560")                 # 设置窗口大小：宽420像素 × 高560像素
        self.root.resizable(False, False)             # 禁止用户拖拽改变窗口大小（保持布局稳定）
        self.root.configure(bg="#1a1a2e")             # 设置窗口背景色为深蓝黑色（暗色主题）

        # ==================== 核心状态变量 ====================
        # state: 当前状态机的状态
        #   "idle"    — 空闲，等待用户点击"开始"
        #   "running" — 主计时器正在运行，用户可以进行寸止操作
        #   "edging"  — 寸止模式，寸止计时器独立运行
        #   "paused"  — 主计时暂停，寸止按钮不可用
        self.state = "idle"

        self.total_seconds = 0   # int: 主计时器的累计秒数（从 session 开始计算）
        self.edge_seconds = 0    # int: 当前这次寸止的累计秒数（进入寸止时清零）
        self.edge_count = 0      # int: 累计完成的寸止次数
        self.edge_records = []   # list[int]: 每次寸止的秒数记录列表
        self._job = None         # str | None: tkinter.after() 返回的定时器 ID，
                                 #            用于取消定时任务，None 表示没有活跃的定时器

        # 构建所有 UI 组件（标签、按钮、文本框等）
        self._build_ui()

    # ═══════════════════════════════════════════════════════════
    #  UI 构建
    # ═══════════════════════════════════════════════════════════

    def _build_ui(self):
        """
        构建全部用户界面组件。
        布局从上到下：
          1. 标题 "⏱ 寸止计时器"
          2. 主计时器大数字显示 + "主计时"小字标签
          3. 寸止信息行（当前寸止计时 + 累计寸止次数）
          4. 寸止按钮（核心交互，大号醒目）
          5. 控制按钮行（开始 / 暂停 / 重置）
          6. 寸止历史记录文本框
        """

        # 定义配色常量，方便统一修改主题
        bg = "#1a1a2e"       # 主背景色：深蓝黑
        fg = "#e0e0e0"       # 通用文字色：浅灰白
        accent = "#e94560"   # 强调色：粉红（用于标题和寸止按钮文字）

        # ── 1. 标题 ──
        title = tk.Label(
            self.root,
            text="⏱ 寸止计时器",
            font=("Microsoft YaHei UI", 16, "bold"),  # 微软雅黑 16号 加粗
            bg=bg,
            fg=accent                                   # 粉红色文字，突出品牌感
        )
        title.pack(pady=(20, 10))  # pack() 布局：上边距20px，下边距10px

        # ── 2. 主计时器（大数字） ──
        self.main_time_label = tk.Label(
            self.root,
            text="00:00:00",                             # 初始显示为全零
            font=("Consolas", 48, "bold"),               # 等宽字体，48号，方便阅读时间
            bg=bg,
            fg="#ffffff"                                  # 纯白色，最醒目
        )
        self.main_time_label.pack(pady=(5, 0))

        # 主计时器下方的说明小字
        self.main_label = tk.Label(
            self.root,
            text="主计时",
            font=("Microsoft YaHei UI", 10),
            bg=bg,
            fg="#888888"                                  # 灰色，降低视觉优先级
        )
        self.main_label.pack()

        # ── 3. 寸止信息行 ──
        # 使用 Frame 容器把两个标签放在同一行
        info_frame = tk.Frame(self.root, bg=bg)
        info_frame.pack(pady=(15, 10))

        # 左侧：当前寸止计时（仅在 EDGING 状态下实时更新）
        self.edge_time_label = tk.Label(
            info_frame,
            text="寸止计时: --:--",                       # 初始无数据
            font=("Consolas", 14),
            bg=bg,
            fg="#ffaa00"                                  # 橙黄色，提醒用户这是寸止状态指示
        )
        self.edge_time_label.pack(side=tk.LEFT, padx=(0, 20))

        # 右侧：累计寸止次数
        self.edge_count_label = tk.Label(
            info_frame,
            text="寸止次数: 0",
            font=("Microsoft YaHei UI", 11),
            bg=bg,
            fg="#cccccc"
        )
        self.edge_count_label.pack(side=tk.LEFT)

        # ── 4. 寸止按钮（核心交互组件） ──
        # 这是整个应用最重要的按钮。设计要点：
        #   - 大字、大尺寸，方便在"关键时刻"快速点击
        #   - 颜色在不同状态间切换：蓝色(待机) ↔ 红色(寸止中)
        #   - 初始为禁用状态，开始计时后才启用
        self.edge_btn = tk.Button(
            self.root,
            text="寸  止",                                # 按钮显示文字
            font=("Microsoft YaHei UI", 22, "bold"),      # 大号加粗
            bg="#16213e",                                 # 默认背景：深蓝色（待机态）
            fg="#e94560",                                 # 默认文字：粉红色
            activebackground="#0f3460",                   # 鼠标按下时的背景色
            activeforeground="#e94560",                   # 鼠标按下时的文字色
            relief=tk.FLAT,                               # 扁平风格，无立体边框
            borderwidth=0,                                # 边框宽度为0
            padx=40,                                      # 按钮内左右留白
            pady=18,                                      # 按钮内上下留白
            cursor="hand2",                               # 鼠标悬停时显示手指光标
            state=tk.DISABLED,                            # 初始禁用（需要先点"开始"）
            command=self._on_edge                         # 绑定回调函数
        )
        self.edge_btn.pack(pady=(10, 15))

        # ── 5. 控制按钮行 ──
        ctrl_frame = tk.Frame(self.root, bg=bg)
        ctrl_frame.pack(pady=(0, 15))

        # [开始] 按钮 — 启动主计时
        self.start_btn = tk.Button(
            ctrl_frame,
            text="开 始",
            font=("Microsoft YaHei UI", 12, "bold"),
            bg="#0f3460", fg="#ffffff",
            activebackground="#16213e", activeforeground="#ffffff",
            relief=tk.FLAT, borderwidth=0,
            padx=18, pady=8,
            cursor="hand2",
            command=self._on_start
        )
        self.start_btn.pack(side=tk.LEFT, padx=5)        # 左排列，左右各留5px间距

        # [暂停] 按钮 — 暂停/继续主计时
        self.pause_btn = tk.Button(
            ctrl_frame,
            text="暂 停",
            font=("Microsoft YaHei UI", 12, "bold"),
            bg="#0f3460", fg="#ffffff",
            activebackground="#16213e", activeforeground="#ffffff",
            relief=tk.FLAT, borderwidth=0,
            padx=18, pady=8,
            cursor="hand2",
            state=tk.DISABLED,                             # 初始禁用
            command=self._on_pause
        )
        self.pause_btn.pack(side=tk.LEFT, padx=5)

        # [重置] 按钮 — 清空所有数据
        self.reset_btn = tk.Button(
            ctrl_frame,
            text="重 置",
            font=("Microsoft YaHei UI", 12, "bold"),
            bg="#0f3460", fg="#ffffff",
            activebackground="#16213e", activeforeground="#ffffff",
            relief=tk.FLAT, borderwidth=0,
            padx=18, pady=8,
            cursor="hand2",
            command=self._on_reset
        )
        self.reset_btn.pack(side=tk.LEFT, padx=5)

        # ── 6. 寸止记录区域 ──
        record_label = tk.Label(
            self.root,
            text="— 寸止记录 —",
            font=("Microsoft YaHei UI", 10, "bold"),
            bg=bg,
            fg="#888888"
        )
        record_label.pack(pady=(5, 5))

        # 记录容器 Frame
        self.record_frame = tk.Frame(self.root, bg=bg)
        self.record_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=(0, 20))

        # 文本框：显示每次寸止的记录（只读模式）
        # 使用 tk.Text 而非 Label，因为需要多行显示和滚动
        self.record_text = tk.Text(
            self.record_frame,
            font=("Consolas", 11),
            bg="#16213e",                                  # 比主背景稍亮一点的深蓝
            fg="#cccccc",
            height=6,                                      # 固定高度6行
            borderwidth=0,
            relief=tk.FLAT,
            state=tk.DISABLED,                             # 初始只读，防止用户编辑
            padx=10,
            pady=8,
            wrap=tk.WORD                                   # 按单词换行
        )
        self.record_text.pack(fill=tk.BOTH, expand=True)   # 填满 Frame

    # ═══════════════════════════════════════════════════════════
    #  计时循环
    # ═══════════════════════════════════════════════════════════

    def _tick(self):
        """
        每秒回调一次（通过 tkinter.after 调度），是计时器的核心循环。
        每次调用执行：
          1. 如果状态为 running 或 edging → 主计时 +1 秒
          2. 如果状态为 edging          → 寸止计时 +1 秒
          3. 更新界面显示
          4. 注册下一秒的回调（形成循环）
        注意：idle 和 paused 状态不会进入 tick，所以计时会停止。
        """
        # 只有当状态是"运行"或"寸止"时才计时
        if self.state in ("running", "edging"):
            self.total_seconds += 1                        # 主计时永远在 running/edging 时递增
            if self.state == "edging":
                self.edge_seconds += 1                     # 寸止计时只在 edging 时递增
            self._update_display()                         # 更新所有显示的数字

            # ★ 关键：注册下一秒的回调
            # tkinter.after(1000, callback) 表示 1000 毫秒后调用 callback
            # 返回值是一个任务 ID，存入 self._job，用于后续取消
            self._job = self.root.after(1000, self._tick)

    def _update_display(self):
        """
        更新界面上所有与时间相关的显示。
        包括：主计时器、寸止计时器、寸止次数
        """
        # 更新主计时器：格式化为 HH:MM:SS
        self.main_time_label.config(text=self._fmt(self.total_seconds))

        # 根据当前状态更新寸止计时显示
        if self.state == "edging":
            # 寸止中：显示实时寸止计时
            self.edge_time_label.config(text=f"寸止计时: {self._fmt(self.edge_seconds)}")
        elif self.state == "running":
            # 正常运行中（非寸止）：显示占位符
            self.edge_time_label.config(text="寸止计时: --:--")

        # 更新累计次数
        self.edge_count_label.config(text=f"寸止次数: {self.edge_count}")

    @staticmethod
    def _fmt(sec: int) -> str:
        """
        将秒数格式化为 HH:MM:SS 字符串。
        - sec // 3600 → 小时数（整除）
        - (sec % 3600) // 60 → 去除小时后剩余秒数，再取分钟
        - sec % 60 → 去除分钟后剩余的秒数
        - :02d 表示不足两位时前面补零（如 5 → "05"）
        """
        h = sec // 3600
        m = (sec % 3600) // 60
        s = sec % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

    # ═══════════════════════════════════════════════════════════
    #  按钮事件处理
    # ═══════════════════════════════════════════════════════════

    def _on_start(self):
        """
        [开始] 按钮点击事件
        仅在 idle 状态下有效：
          状态切换：idle → running
          副作用：
            - "开始"按钮变为"运行中"并禁用（防止重复点击）
            - "暂停"按钮启用
            - "寸止"按钮启用
            - 启动计时循环 _tick()
        """
        if self.state == "idle":
            self.state = "running"                         # 状态切换
            self.start_btn.config(text="运 行 中", state=tk.DISABLED)  # 按钮文本变为"运行中"并禁用
            self.pause_btn.config(state=tk.NORMAL)          # 启用暂停按钮
            self.edge_btn.config(state=tk.NORMAL, bg="#16213e")  # 启用寸止按钮，恢复蓝色
            self._tick()                                    # 启动计时循环

    def _on_pause(self):
        """
        [暂停/继续] 按钮点击事件
        双功能按钮，根据当前状态切换行为：
          running → paused：暂停主计时，禁用寸止按钮，取消定时器
          paused → running：恢复主计时，启用寸止按钮，重新启动定时器
        注意：在 idle 和 edging 状态下无效
        """
        if self.state == "running":
            # 正在运行 → 暂停
            self.state = "paused"
            self.pause_btn.config(text="继 续")            # 按钮文字改为"继续"
            self.edge_btn.config(state=tk.DISABLED)         # 暂停时不允许寸止
            self._cancel_tick()                             # 取消定时器，停止计时
        elif self.state == "paused":
            # 已暂停 → 恢复运行
            self.state = "running"
            self.pause_btn.config(text="暂 停")            # 按钮文字改回"暂停"
            self.edge_btn.config(state=tk.NORMAL)           # 恢复寸止按钮
            self._tick()                                    # 重新启动计时循环

    def _on_edge(self):
        """
        [寸止] 按钮点击事件 —— 这是核心交互逻辑
        ============================================

        双功能按钮，根据当前状态切换行为：

        ① running → edging（进入寸止）：
           - 状态切换到 edging
           - 寸止秒数归零，开始独立计时
           - 按钮变红，文字变为"停止寸止"
           - 主计时继续在后台运行（不容易打断）

        ② edging → running（退出寸止）：
           - 累计寸止次数 +1
           - 将本次寸止秒数存入 records 列表
           - 将本次记录写入文本框
           - 寸止秒数归零
           - 按钮恢复蓝色，文字改回"寸止"
           - 状态回到 running，主计时继续
        """
        if self.state == "running":
            # ── 进入寸止模式 ──
            self.state = "edging"                          # 切换状态
            self.edge_seconds = 0                          # 寸止秒数从零开始
            self.edge_btn.config(
                text="停 止 寸 止",                         # 改变按钮文字
                bg="#b00020",                              # 背景变深红（警示色）
                fg="#ffffff",                              # 文字变白（红底白字更醒目）
                activebackground="#d00028"                 # 按下时稍亮的红色
            )

        elif self.state == "edging":
            # ── 退出寸止模式，记录本次数据 ──
            self.edge_count += 1                            # 次数 +1
            self.edge_records.append(self.edge_seconds)     # 记录本次寸止时长（秒）
            self._append_record(self.edge_count, self.edge_seconds)  # 写入文本框
            self.edge_seconds = 0                           # 归零，准备下次使用
            self.state = "running"                          # 回到运行状态
            # 恢复按钮的蓝色外观
            self.edge_btn.config(
                text="寸  止",
                bg="#16213e",
                fg="#e94560",
                activebackground="#0f3460"
            )
            # 更新界面上寸止相关显示
            self.edge_time_label.config(text="寸止计时: --:--")
            self.edge_count_label.config(text=f"寸止次数: {self.edge_count}")

    def _on_reset(self):
        """
        [重置] 按钮点击事件
        ====================
        将所有状态和数据恢复到初始值，可在任何状态下调用。
        执行步骤：
          1. 取消计时循环
          2. 状态 → idle
          3. 所有计数器归零
          4. 清空记录列表
          5. 恢复所有 UI 组件到初始外观和状态
        """
        self._cancel_tick()                                # 停止计时循环

        # 重置所有状态变量
        self.state = "idle"
        self.total_seconds = 0
        self.edge_seconds = 0
        self.edge_count = 0
        self.edge_records.clear()                          # 清空列表

        # 重置 UI 显示
        self.main_time_label.config(text="00:00:00")
        self.edge_time_label.config(text="寸止计时: --:--")
        self.edge_count_label.config(text="寸止次数: 0")

        # 恢复按钮状态
        self.start_btn.config(text="开 始", state=tk.NORMAL)         # "开始"可用
        self.pause_btn.config(text="暂 停", state=tk.DISABLED)        # "暂停"禁用
        self.edge_btn.config(
            state=tk.DISABLED, text="寸  止",
            bg="#16213e", fg="#e94560"
        )                                                              # "寸止"禁用

        self._clear_records()                              # 清空记录文本框

    # ═══════════════════════════════════════════════════════════
    #  辅助方法
    # ═══════════════════════════════════════════════════════════

    def _cancel_tick(self):
        """
        取消 tkinter.after() 的定时回调。
        通过之前保存的 self._job ID 来取消，_job 为 None 则跳过。
        取消后必须将 _job 设为 None，防止重复取消导致错误。
        """
        if self._job is not None:
            self.root.after_cancel(self._job)              # 取消定时任务
            self._job = None                               # 清除 ID

    def _append_record(self, num: int, sec: int):
        """
        向记录文本框追加一条寸止记录。

        参数：
          num — int: 第几次寸止（从 1 开始）
          sec — int: 本次寸止持续秒数

        由于文本框在创建时设为 DISABLED（只读），写入前需要临时
        切换为 NORMAL → 写入 → 再切回 DISABLED。
        """
        self.record_text.config(state=tk.NORMAL)           # 临时允许编辑
        line = f"#{num}  寸止 {self._fmt(sec)}\n"          # 格式化：如 "#1  寸止 00:00:32"
        self.record_text.insert(tk.END, line)              # 在末尾追加
        self.record_text.see(tk.END)                       # 自动滚动到最新记录
        self.record_text.config(state=tk.DISABLED)         # 恢复只读

    def _clear_records(self):
        """
        清空记录文本框中的所有内容。
        "1.0" 表示第1行第0个字符（即文档开头），tk.END 表示文档末尾。
        同样需要临时切换编辑状态。
        """
        self.record_text.config(state=tk.NORMAL)
        self.record_text.delete("1.0", tk.END)
        self.record_text.config(state=tk.DISABLED)

    # ═══════════════════════════════════════════════════════════
    #  启动入口
    # ═══════════════════════════════════════════════════════════

    def run(self):
        """
        启动 tkinter 主事件循环。
        mainloop() 会阻塞当前线程，持续监听用户输入（点击、键盘等），
        直到用户关闭窗口才会返回。这是所有 tkinter 应用的必经步骤。
        """
        self.root.mainloop()


# ── 程序入口 ──
# __name__ 是 Python 的内置变量：
#   - 直接运行此文件时，__name__ == "__main__"，执行 if 块内容
#   - 被其他文件 import 时，__name__ == "edging_timer"，不执行
# 这种写法使得该文件既可以作为脚本直接运行，也可以被其他模块导入复用。
if __name__ == "__main__":
    # 创建 EdgingTimer 实例并启动应用
    EdgingTimer().run()
