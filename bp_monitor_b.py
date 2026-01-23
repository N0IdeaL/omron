import tkinter as tk
from tkinter import font
import requests

# 配置
IP = "  " # 接血压计的电脑的IP
DATA_URL = f"http://{IP}:8080/data"
REFRESH_RATE = 1000  # 刷新频率 (毫秒)
AUTH_USERNAME = "user"   # 用户名任意
AUTH_PASSWORD = "" # 网页认证密码

# 颜色定义
COLORS = {
    'bg': '#16213e',        # 背景深蓝
    'card_bg': '#0b1020',   # 卡片背景更深
    'text': '#ffffff',      # 普通文本
    'success': '#4ecca3',   # 正常 (绿色)
    'warning': '#ffd369',   # 异常 (黄色)
    'offline': '#ff6b6b'    # 断开 (红色)
}

class BPMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("BP Monitor")
        self.root.geometry("380x160") # 小巧的窗口尺寸
        self.root.configure(bg=COLORS['bg'])
        
        # --- 核心功能：窗口永远置顶 ---
        self.root.attributes('-topmost', True)
        
        # 初始化UI布局
        self.setup_ui()
        
        # 开始轮询数据
        self.update_data()

    def setup_ui(self):
        # 顶部状态栏
        self.status_var = tk.StringVar(value="等待连接...")
        self.time_var = tk.StringVar(value="--:--:--")
        
        top_frame = tk.Frame(self.root, bg=COLORS['bg'])
        top_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(top_frame, textvariable=self.status_var, fg=COLORS['text'], bg=COLORS['bg'], font=("Arial", 9)).pack(side='left')
        tk.Label(top_frame, textvariable=self.time_var, fg=COLORS['text'], bg=COLORS['bg'], font=("Arial", 9)).pack(side='right')

        # 数据网格区域
        grid_frame = tk.Frame(self.root, bg=COLORS['bg'])
        grid_frame.pack(expand=True, fill='both', padx=10, pady=5)
        
        # 配置列权重 (3列等宽)
        grid_frame.columnconfigure(0, weight=1)
        grid_frame.columnconfigure(1, weight=1)
        grid_frame.columnconfigure(2, weight=1)

        # 创建三个显示组件
        self.sys_label = self.create_value_card(grid_frame, 0, "SYS")
        self.dia_label = self.create_value_card(grid_frame, 1, "DIA")
        self.pul_label = self.create_value_card(grid_frame, 2, "PULSE")

    def create_value_card(self, parent, col, title):
        frame = tk.Frame(parent, bg=COLORS['card_bg'], bd=0)
        frame.grid(row=0, column=col, sticky="nsew", padx=4, pady=4)
        
        # 标题
        tk.Label(frame, text=title, fg="#888888", bg=COLORS['card_bg'], font=("Arial", 8)).pack(pady=(10, 0))
        
        # 数值标签 (保存引用以便后续更新颜色和数值)
        lbl = tk.Label(frame, text="--", fg=COLORS['text'], bg=COLORS['card_bg'], font=("Arial", 32, "bold"))
        lbl.pack(pady=(0, 10))
        return lbl

    def get_bp_color(self, value, bp_type):
        """ 根据用户要求的逻辑返回颜色 """
        if value is None:
            return COLORS['text']
            
        val = int(value)
        
        if bp_type == 'sys':
            if val < 90:
                return COLORS['warning']
            elif val < 140:
                return COLORS['success']
            else:
                return COLORS['warning']
        else: # dia
            if val < 60:
                return COLORS['warning']
            elif val < 90:
                return COLORS['success']
            else:
                return COLORS['warning']

    def update_data(self):
        try:
            # 发起请求
            resp = requests.get(
                DATA_URL,
                auth=(AUTH_USERNAME, AUTH_PASSWORD),
                timeout=1
            )
            data = resp.json()
            
            # 解析数据
            sys_val = data.get("sys")
            dia_val = data.get("dia")
            pul_val = data.get("pulse")
            ts = data.get("timestamp")
            status = data.get("status")

            # 1. 更新数值
            self.sys_label.config(text=str(sys_val) if sys_val else "--")
            self.dia_label.config(text=str(dia_val) if dia_val else "--")
            self.pul_label.config(text=str(pul_val) if pul_val else "--")

            # 2. 更新颜色
            self.sys_label.config(fg=self.get_bp_color(sys_val, 'sys'))
            self.dia_label.config(fg=self.get_bp_color(dia_val, 'dia'))
            
            # 心率通常没有特定逻辑，暂定为白色，或您可以自己加
            self.pul_label.config(fg=COLORS['success'] if pul_val else COLORS['text'])

            # 3. 更新顶部状态
            self.status_var.set(f"状态: {status}")
            if ts:
                # 假设时间戳格式为 "YYYY-MM-DD HH:MM:SS"，只取后面时间
                time_part = ts.split(" ")[1] if " " in ts else ts
                self.time_var.set(time_part)
            else:
                self.time_var.set("--:--:--")

        except Exception as e:
            self.status_var.set("连接断开")
            self.sys_label.config(text="--", fg=COLORS['offline'])
            self.dia_label.config(text="--", fg=COLORS['offline'])
            self.pul_label.config(text="--", fg=COLORS['offline'])
        
        # 设定下一次刷新
        self.root.after(REFRESH_RATE, self.update_data)

if __name__ == "__main__":
    root = tk.Tk()
    app = BPMonitorApp(root)
    root.mainloop()