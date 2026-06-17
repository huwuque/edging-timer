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

import ctypes              # 用于启用 Windows 高 DPI 感知，消除字体模糊
import tkinter as tk       # Python 标准 GUI 库，用于构建桌面窗口
from tkinter import ttk     # tkinter 的主题组件（本次未使用，预留扩展）
from PIL import Image, ImageTk  # Pillow：加载 JPG 奖励图片
# import time               # 未直接使用（通过 tkinter.after() 实现计时）

# ── 启用高 DPI 感知，确保文字高清无模糊 ──
# 必须在创建任何窗口之前调用，否则无效
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per Monitor DPI v2 (Win 10 1703+)
except Exception:
    pass


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
        self.root.geometry("460x620")                 # 初始窗口大小
        self.root.minsize(400, 500)                   # 最小尺寸，防止布局被压坏
        self.root.configure(bg="#EDEAE5")             # 莫兰迪暖灰白底色（canvas 基调）

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
        self._reward_milestones = set()  # set[int]: 已弹出过奖励的寸止秒数里程碑

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

        浅色高级主题：Apple / Linear 风格极简设计
        """

        # 定义莫兰迪配色常量 — 低饱和度、灰调、温暖柔和
        bg        = "#EDEAE5"   # 主背景：暖灰白（画布基调）
        surface   = "#F7F5F1"   # 卡片/文本框背景：暖白
        fg        = "#4E4A46"   # 主文字：暖深灰褐（永不纯黑）
        fg_sec    = "#9B9690"   # 次要文字：暖中灰
        accent    = "#B0A8A0"   # 主强调色：暖灰褐 taupe
        accent_hv = "#A09890"   # taupe 按下态
        danger    = "#C4A5A5"   # 寸止中：莫兰迪尘玫瑰（dusty rose）
        danger_hv = "#B89494"   # 尘玫瑰按下态
        btn_sec   = "#E0DCD5"   # 次要按钮：暖浅灰
        btn_sec_hv="#D4CFC7"   # 次要按钮按下态
        border    = "#D5D0C8"   # 边框：暖灰

        # ── 1. 标题 ──
        title = tk.Label(
            self.root,
            text="寸止计时器",
            font=("Microsoft YaHei UI", 16, "bold"),
            bg=bg,
            fg="#6B6560"                               # 暖灰褐标题
        )
        title.pack(pady=(28, 12))

        # ── 2. 主计时器（大数字） ──
        self.main_time_label = tk.Label(
            self.root,
            text="00:00:00",
            font=("Segoe UI", 54, "bold"),             # Segoe UI 比例字体，极简现代
            bg=bg,
            fg="#4E4A46"                               # 暖深灰褐，不刺眼
        )
        self.main_time_label.pack(pady=(8, 0))

        # 主计时器下方的说明小字
        self.main_label = tk.Label(
            self.root,
            text="主计时",
            font=("Microsoft YaHei UI", 10),
            bg=bg,
            fg=fg_sec                                   # 中灰色，降低视觉权重
        )
        self.main_label.pack()

        # ── 3. 寸止信息行 ──
        info_frame = tk.Frame(self.root, bg=bg)
        info_frame.pack(pady=(20, 14))

        # 左侧：当前寸止计时
        self.edge_time_label = tk.Label(
            info_frame,
            text="寸止计时  --:--",
            font=("Cascadia Mono", 13),                 # Windows 11 现代等宽字体
            bg=bg,
            fg=fg_sec
        )
        self.edge_time_label.pack(side=tk.LEFT, padx=(0, 22))

        # 右侧：累计寸止次数
        self.edge_count_label = tk.Label(
            info_frame,
            text="次数 0",
            font=("Microsoft YaHei UI", 11),
            bg=bg,
            fg=fg_sec
        )
        self.edge_count_label.pack(side=tk.LEFT)

        # ── 4. 寸止按钮（核心交互） ──
        self.edge_btn = tk.Button(
            self.root,
            text="寸  止",
            font=("Microsoft YaHei UI", 24, "bold"),
            bg=accent,                                   # 靛蓝背景
            fg="#FFFFFF",                                # 白色文字
            activebackground=accent_hv,                  # 按下时稍深
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            borderwidth=0,
            padx=44,
            pady=20,
            cursor="hand2",
            state=tk.DISABLED,
            command=self._on_edge
        )
        self.edge_btn.pack(pady=(12, 20))

        # ── 5. 控制按钮行 ──
        ctrl_frame = tk.Frame(self.root, bg=bg)
        ctrl_frame.pack(pady=(0, 20))

        # [开始] — 主要操作，靛蓝实心
        self.start_btn = tk.Button(
            ctrl_frame,
            text="开 始",
            font=("Microsoft YaHei UI", 12, "bold"),
            bg=accent, fg="#FFFFFF",
            activebackground=accent_hv, activeforeground="#FFFFFF",
            relief=tk.FLAT, borderwidth=0,
            padx=20, pady=10,
            cursor="hand2",
            command=self._on_start
        )
        self.start_btn.pack(side=tk.LEFT, padx=6)

        # [暂停] — 次要操作，浅灰背景
        self.pause_btn = tk.Button(
            ctrl_frame,
            text="暂 停",
            font=("Microsoft YaHei UI", 12, "bold"),
            bg=btn_sec, fg=fg,
            activebackground=btn_sec_hv, activeforeground=fg,
            relief=tk.FLAT, borderwidth=0,
            padx=20, pady=10,
            cursor="hand2",
            state=tk.DISABLED,
            command=self._on_pause
        )
        self.pause_btn.pack(side=tk.LEFT, padx=6)

        # [重置] — 次要操作，浅灰背景
        self.reset_btn = tk.Button(
            ctrl_frame,
            text="重 置",
            font=("Microsoft YaHei UI", 12, "bold"),
            bg=btn_sec, fg=fg,
            activebackground=btn_sec_hv, activeforeground=fg,
            relief=tk.FLAT, borderwidth=0,
            padx=20, pady=10,
            cursor="hand2",
            command=self._on_reset
        )
        self.reset_btn.pack(side=tk.LEFT, padx=6)

        # ── 6. 寸止记录区域 ──
        record_label = tk.Label(
            self.root,
            text="寸止记录",
            font=("Microsoft YaHei UI", 10, "bold"),
            bg=bg,
            fg=fg_sec
        )
        record_label.pack(pady=(6, 8))

        # 记录容器 Frame — 白色卡片样式
        self.record_frame = tk.Frame(self.root, bg=surface, highlightbackground=border, highlightthickness=1)
        self.record_frame.pack(fill=tk.BOTH, expand=True, padx=36, pady=(0, 24))

        # 文本框：白色卡片 + 深色文字
        self.record_text = tk.Text(
            self.record_frame,
            font=("Cascadia Mono", 11),
            bg=surface,
            fg="#4E4A46",
            height=6,
            borderwidth=0,
            relief=tk.FLAT,
            state=tk.DISABLED,
            padx=14,
            pady=12,
            wrap=tk.WORD
        )
        self.record_text.pack(fill=tk.BOTH, expand=True)

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

            # 主计时每 10 秒弹出奖励图片
            if self.total_seconds > 0 and self.total_seconds % 10 == 0:
                if self.total_seconds not in self._reward_milestones:
                    self._reward_milestones.add(self.total_seconds)
                    self._show_reward()

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
            self.edge_time_label.config(text=f"寸止计时  {self._fmt(self.edge_seconds)}")
        elif self.state == "running":
            # 正常运行中（非寸止）：显示占位符
            self.edge_time_label.config(text="寸止计时  --:--")

        # 更新累计次数
        self.edge_count_label.config(text=f"次数 {self.edge_count}")

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
            self._reward_milestones.clear()               # 新 session 开始，清空奖励里程碑
            self.start_btn.config(text="运 行 中", state=tk.DISABLED)  # 按钮文本变为"运行中"并禁用
            self.pause_btn.config(state=tk.NORMAL)          # 启用暂停按钮
            self.edge_btn.config(state=tk.NORMAL, bg="#B0A8A0")  # 启用寸止按钮，taupe 背景
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
                bg="#C4A5A5",                              # 莫兰迪尘玫瑰（dusty rose）
                fg="#FFFFFF",                              # 白色文字
                activebackground="#B89494"                 # 按下时稍深
            )

        elif self.state == "edging":
            # ── 退出寸止模式，记录本次数据 ──
            self.edge_count += 1                            # 次数 +1
            self.edge_records.append(self.edge_seconds)     # 记录本次寸止时长（秒）
            self._append_record(self.edge_count, self.edge_seconds)  # 写入文本框
            self.edge_seconds = 0                           # 归零，准备下次使用
            self.state = "running"                          # 回到运行状态
            # 恢复 taupe 外观
            self.edge_btn.config(
                text="寸  止",
                bg="#B0A8A0",
                fg="#FFFFFF",
                activebackground="#A09890"
            )
            # 更新界面上寸止相关显示
            self.edge_time_label.config(text="寸止计时  --:--")
            self.edge_count_label.config(text=f"次数 {self.edge_count}")

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
        self._reward_milestones.clear()               # 清空奖励里程碑

        # 重置 UI 显示
        self.main_time_label.config(text="00:00:00")
        self.edge_time_label.config(text="寸止计时  --:--")
        self.edge_count_label.config(text="次数 0")

        # 恢复按钮状态
        self.start_btn.config(text="开 始", state=tk.NORMAL)         # "开始"可用
        self.pause_btn.config(text="暂 停", state=tk.DISABLED)        # "暂停"禁用
        self.edge_btn.config(
            state=tk.DISABLED, text="寸  止",
            bg="#B0A8A0", fg="#FFFFFF"
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
        line = f"#{num}    {self._fmt(sec)}\n"               # 极简格式：如 "#1    00:00:32"
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

    def _show_reward(self):
        """
        弹出奖励图片弹窗 — 主计时每过 10 秒触发一次。

        弹窗特性：
          - 无边框居中显示
          - 图片缩放到 400×400 以内
          - 2 秒后自动关闭
          - 加载失败时静默跳过
        """
        try:
            img = Image.open("奖励图片.jpg")
            img.thumbnail((400, 400), Image.LANCZOS)           # 等比缩放
            photo = ImageTk.PhotoImage(img)

            reward = tk.Toplevel(self.root)
            reward.overrideredirect(True)                      # 无边框窗口
            reward.configure(bg="#EDEAE5")                      # 莫兰迪底色

            label = tk.Label(reward, image=photo, bg="#EDEAE5")
            label.image = photo                                 # ★ 保持引用，防止被 GC 回收
            label.pack()

            # 居中屏幕
            reward.update_idletasks()
            sw = reward.winfo_screenwidth()
            sh = reward.winfo_screenheight()
            w = reward.winfo_reqwidth()
            h = reward.winfo_reqheight()
            x = (sw - w) // 2
            y = (sh - h) // 2
            reward.geometry(f"+{x}+{y}")

            reward.after(2000, reward.destroy)                 # 2 秒后自动销毁
        except Exception:
            pass  # 图片缺失或损坏时静默跳过，不影响主程序

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
