#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OMRON HBP-9030 血压计数据监测程序
通过USB串口读取血压计数据并在图形界面显示

功能特点：
- 自动检测串口设备
- 支持多种数据格式自动解析
- 模拟模式用于测试（无需真实设备）
- 血压值颜色提示
- 历史记录保存
- 跨平台支持（Windows / Linux / 树莓派）
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import re
import random
import time
import os
import sys
import platform
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, List, Callable
import queue

# 尝试导入pyserial，如果失败则提供友好提示
try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False


# ============== 平台检测与适配 ==============
class PlatformConfig:
    """跨平台配置"""
    
    def __init__(self):
        self.system = platform.system()  # 'Windows', 'Linux', 'Darwin'
        self.machine = platform.machine()  # 'x86_64', 'armv7l', 'aarch64'
        self.is_windows = self.system == 'Windows'
        self.is_linux = self.system == 'Linux'
        self.is_mac = self.system == 'Darwin'
        self.is_raspberry_pi = self._detect_raspberry_pi()
        
        # 根据平台设置字体
        if self.is_windows:
            self.font_family = 'Microsoft YaHei UI'
            self.font_mono = 'Consolas'
        elif self.is_mac:
            self.font_family = 'PingFang SC'
            self.font_mono = 'Menlo'
        else:  # Linux / 树莓派
            self.font_family = 'Noto Sans CJK SC'  # 或 'WenQuanYi Micro Hei'
            self.font_mono = 'DejaVu Sans Mono'
        
        # 根据平台设置窗口尺寸
        if self.is_raspberry_pi:
            # 树莓派通常使用小屏幕（如7寸800x480）
            self.window_size = "800x480"
            self.window_min = (750, 450)
            self.font_scale = 0.85  # 字体缩小
            self.fullscreen = True  # 默认全屏
        else:
            self.window_size = "350x200"
            self.window_min = (400, 250)
            self.font_scale = 1
            self.fullscreen = False
        
        # 串口路径前缀
        if self.is_windows:
            self.serial_prefix = "COM"
        else:
            self.serial_prefix = "/dev/tty"
    
    def _detect_raspberry_pi(self) -> bool:
        """检测是否为树莓派"""
        if not self.is_linux:
            return False
        try:
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()
                return 'Raspberry Pi' in cpuinfo or 'BCM' in cpuinfo
        except Exception:
            pass
        # 检查是否是ARM架构的Linux
        return self.machine in ('armv7l', 'armv6l', 'aarch64')
    
    def get_font(self, size: int, weight: str = 'normal') -> tuple:
        """获取适配平台的字体"""
        scaled_size = int(size * self.font_scale)
        return (self.font_family, scaled_size, weight)
    
    def get_mono_font(self, size: int) -> tuple:
        """获取等宽字体"""
        scaled_size = int(size * self.font_scale)
        return (self.font_mono, scaled_size)
    
    def __str__(self):
        return f"Platform: {self.system} ({self.machine}), RaspberryPi: {self.is_raspberry_pi}"


# 全局平台配置
PLATFORM = PlatformConfig()


# ============== 日志配置 ==============
import logging

def setup_logging():
    """配置日志，处理打包后的路径问题"""
    # 获取程序所在目录
    if getattr(sys, 'frozen', False):
        # 打包后的exe
        app_dir = os.path.dirname(sys.executable)
    else:
        # 普通Python脚本
        app_dir = os.path.dirname(os.path.abspath(__file__))
    
    log_file = os.path.join(app_dir, 'bp_monitor.log')
    
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()


# ============== 数据类 ==============
@dataclass
class BloodPressureReading:
    """血压读数数据类"""
    systolic: int           # 收缩压 (mmHg)
    diastolic: int          # 舒张压 (mmHg)
    pulse: int              # 心率 (bpm)
    timestamp: datetime     # 测量时间
    raw_data: str = ""      # 原始数据（用于调试）
    
    def __str__(self):
        return f"{self.timestamp.strftime('%Y-%m-%d %H:%M')}  {self.systolic}/{self.diastolic}  {self.pulse} bpm"


# ============== 数据解析器 ==============
class DataParser:
    """
    HBP-9030 数据解析器
    固定格式: YYYY.MM.DD.HH.MM.ID(20).e(1).SYS(3).DIA(3).PR(3).MOTION+CR+LF
    """
    
    @staticmethod
    def parse(data: bytes) -> Optional[BloodPressureReading]:
        """
        尝试解析血压数据
        仅支持 data_format.md 指定的固定格式
        """
        try:
            if not data:
                return None

            # 尝试不同的编码方式解码，保证不抛异常
            text = ""
            for encoding in ['ascii', 'utf-8', 'latin-1', 'gbk']:
                try:
                    text = data.decode(encoding, errors='ignore').strip()
                    if text:
                        break
                except (UnicodeDecodeError, LookupError):
                    continue

            if not text:
                return None

            logger.debug(f"接收原始数据: {repr(text)}")
            # logger.debug(f"十六进制: {data.hex()}")

            result = DataParser._parse_format_hbp9030(text)
            if result:
                result.raw_data = text
                logger.info(f"解析成功: SYS={result.systolic}, DIA={result.diastolic}, PR={result.pulse}")
            else:
                logger.debug("解析失败: 未匹配固定格式")

            return result

        except Exception as e:
            logger.error(f"解析数据时出错: {e}", exc_info=True)
            return None
    
    @staticmethod
    def _parse_format_hbp9030(text: str) -> Optional[BloodPressureReading]:
        """
        HBP-9030 专用格式解析
        固定格式: YYYY,MM,DD,HH,MM,ID(20),e(1),SYS(3),DIA(3),PR(3),MOTION+CR+LF
        """
        try:
            # clean = text.strip().replace("\x00", "")
            # parts = [p.strip() for p in clean.split(',') if p.strip() != ""]
            parts = text.strip().split(",")
            if len(parts) < 11:
                return None

            if len(parts) > 11:
                parts = parts[:11]

            year_s, mon_s, day_s, hour_s, min_s, device_id, err_s, sys_s, dia_s, pr_s, motion_s = parts

            if not (year_s.isdigit() and len(year_s) == 4):
                return None
            if not (mon_s.isdigit() and len(mon_s) == 2):
                return None
            if not (day_s.isdigit() and len(day_s) == 2):
                return None
            if not (hour_s.isdigit() and len(hour_s) == 2):
                return None
            if not (min_s.isdigit() and len(min_s) == 2):
                return None
            # if not (device_id.isdigit() and len(device_id) == 20):
            #     return None

            try:
                sys_val = int(sys_s)
                dia_val = int(dia_s)
                pr_val = int(pr_s)
            except ValueError:
                return None

            if not (60 <= sys_val <= 300 and 30 <= dia_val <= 200 and 30 <= pr_val <= 200):
                return None
            if sys_val <= dia_val:
                return None

            try:
                timestamp = datetime(
                    int(year_s), int(mon_s), int(day_s),
                    int(hour_s), int(min_s)
                )
            except ValueError:
                timestamp = datetime.now()

            return BloodPressureReading(
                systolic=sys_val,
                diastolic=dia_val,
                pulse=pr_val,
                timestamp=timestamp
            )
        except Exception as e:
            logger.debug(f"HBP-9030格式解析失败: {e}")
        return None


# ============== 模拟器 ==============
class Simulator:
    """模拟血压数据生成器，用于测试"""
    
    def __init__(self, on_data_received: Callable[[BloodPressureReading], None] = None,
                 on_raw_data: Callable[[bytes], None] = None,
                 on_status_change: Callable[[str], None] = None):
        self.on_data_received = on_data_received
        self.on_raw_data = on_raw_data
        self.on_status_change = on_status_change
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        
    def start(self, interval: float = 5.0):
        """开始模拟"""
        if not self.is_running:
            self.is_running = True
            self.interval = interval
            self.thread = threading.Thread(target=self._simulate_loop, daemon=True)
            self.thread.start()
            if self.on_status_change:
                self.on_status_change("模拟模式运行中")
            logger.info("模拟器已启动")
    
    def stop(self):
        """停止模拟"""
        self.is_running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        if self.on_status_change:
            self.on_status_change("模拟模式已停止")
        logger.info("模拟器已停止")
    
    def _simulate_loop(self):
        """模拟数据生成循环"""
        while self.is_running:
            # 生成随机但合理的血压数据
            sys_val = random.randint(100, 160)
            dia_val = random.randint(60, 100)
            pr_val = random.randint(55, 95)
            
            # 确保收缩压大于舒张压
            if dia_val >= sys_val:
                dia_val = sys_val - 20
            
            reading = BloodPressureReading(
                systolic=sys_val,
                diastolic=dia_val,
                pulse=pr_val,
                timestamp=datetime.now(),
                raw_data=f"[模拟] SYS:{sys_val} DIA:{dia_val} PR:{pr_val}"
            )
            
            # 模拟原始数据
            raw_data = f"{sys_val},{dia_val},{pr_val}\r\n".encode('ascii')
            
            if self.on_raw_data:
                self.on_raw_data(raw_data)
            
            if self.on_data_received:
                self.on_data_received(reading)
            
            logger.info(f"[模拟] 生成数据: {sys_val}/{dia_val} {pr_val}")
            
            # 等待间隔
            time.sleep(self.interval)
    
    @property
    def is_connected(self) -> bool:
        return self.is_running


# ============== 串口连接 ==============
class SerialConnection:
    """串口连接管理器"""
    
    def __init__(self, on_data_received: Callable[[BloodPressureReading], None] = None,
                 on_raw_data: Callable[[bytes], None] = None,
                 on_status_change: Callable[[str], None] = None):
        self.serial_port = None
        self.is_running = False
        self.read_thread: Optional[threading.Thread] = None
        self.on_data_received = on_data_received
        self.on_raw_data = on_raw_data
        self.on_status_change = on_status_change
        
    @staticmethod
    def list_ports() -> List[str]:
        """获取可用串口列表"""
        if not SERIAL_AVAILABLE:
            return []
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]
    
    @staticmethod
    def get_port_info() -> List[tuple]:
        """获取串口详细信息"""
        if not SERIAL_AVAILABLE:
            return []
        ports = serial.tools.list_ports.comports()
        return [(port.device, port.description) for port in ports]
    
    def connect(self, port: str, baudrate: int = 9600, timeout: float = 1.0) -> bool:
        """连接到串口"""
        if not SERIAL_AVAILABLE:
            self._notify_status("错误: 未安装pyserial库")
            return False
            
        try:
            if self.serial_port and self.serial_port.is_open:
                self.disconnect()
            
            self.serial_port = serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=timeout
            )
            
            if self.serial_port.is_open:
                logger.info(f"已连接到 {port}, 波特率: {baudrate}")
                self._notify_status(f"已连接到 {port}")
                self.start_reading()
                return True
            return False
            
        except serial.SerialException as e:
            error_msg = str(e)
            # 提供更友好的错误提示
            if "PermissionError" in error_msg or "拒绝访问" in error_msg:
                error_msg = f"{port} 被占用，请关闭其他使用该端口的程序"
            elif "FileNotFoundError" in error_msg or "找不到" in error_msg:
                error_msg = f"{port} 不存在，请检查设备连接"
            
            logger.error(f"连接失败: {error_msg}")
            self._notify_status(f"连接失败: {error_msg}")
            return False
        except Exception as e:
            logger.error(f"连接时发生未知错误: {e}")
            self._notify_status(f"连接错误: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        self.stop_reading()
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.close()
            except Exception as e:
                logger.error(f"关闭串口时出错: {e}")
            logger.info("已断开连接")
            self._notify_status("已断开连接")
    
    def start_reading(self):
        """开始读取数据"""
        if not self.is_running:
            self.is_running = True
            self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
            self.read_thread.start()
    
    def stop_reading(self):
        """停止读取数据"""
        self.is_running = False
        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=2.0)
    
    def _read_loop(self):
        """数据读取循环"""
        buffer = b''
        last_status_time = time.time()
        bytes_received_total = 0
        
        logger.info("开始监听串口数据...")
        
        while self.is_running and self.serial_port and self.serial_port.is_open:
            try:
                # 每10秒输出一次状态，帮助诊断
                now = time.time()
                if now - last_status_time >= 10:
                    if bytes_received_total == 0:
                        logger.warning("【诊断】已等待10秒，未收到任何数据。请检查：")
                        logger.warning("  1. 血压计是否开启了USB输出功能（功能选择模式-项号32）")
                        logger.warning("  2. 波特率是否正确（尝试9600/19200/38400/115200）")
                        logger.warning("  3. USB线是否为数据线（非纯充电线）")
                        logger.warning("  4. 血压计是否完成了一次测量")
                    else:
                        logger.info(f"【诊断】已接收 {bytes_received_total} 字节")
                    last_status_time = now
                
                if self.serial_port.in_waiting > 0:
                    data = self.serial_port.read(self.serial_port.in_waiting)
                    buffer += data
                    bytes_received_total += len(data)
                    
                    logger.debug(f"收到 {len(data)} 字节: {data.hex()} | {data!r}")
                    
                    if self.on_raw_data:
                        self.on_raw_data(data)
                    
                    while b'\r' in buffer or b'\n' in buffer:
                        end_pos = -1
                        for i, b in enumerate(buffer):
                            if b in (0x0D, 0x0A):
                                end_pos = i
                                break
                        
                        if end_pos >= 0:
                            line = buffer[:end_pos]
                            buffer = buffer[end_pos + 1:]
                            
                            if line.strip():
                                self._process_data(line)
                    
                    if len(buffer) > 256:
                        self._process_data(buffer)
                        buffer = b''
                else:
                    time.sleep(0.05)  # 避免CPU占用过高
                        
            except serial.SerialException as e:
                logger.error(f"读取数据时出错: {e}")
                self._notify_status(f"读取错误: {e}")
                break
            except Exception as e:
                logger.error(f"处理数据时出错: {e}")
    
    def _process_data(self, data: bytes):
        """处理接收到的数据"""
        reading = DataParser.parse(data)
        if reading and self.on_data_received:
            self.on_data_received(reading)
    
    def _notify_status(self, status: str):
        """通知状态变化"""
        if self.on_status_change:
            self.on_status_change(status)
    
    @property
    def is_connected(self) -> bool:
        return self.serial_port is not None and self.serial_port.is_open


# ============== 图形界面 ==============
class BloodPressureMonitorGUI:
    """血压监测图形界面"""
    
    # 颜色主题
    COLORS = {
        'bg_dark': '#1a1a2e',
        'bg_medium': '#16213e',
        'bg_light': '#0f3460',
        'accent': '#e94560',
        'accent_light': '#ff6b6b',
        'text_primary': '#ffffff',
        'text_secondary': '#a0a0a0',
        'success': '#4ecca3',
        'warning': '#ffd369',
        'danger': '#ff6b6b',
        'simulation': '#9d4edd',
    }
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("邵逸夫医院大运河 OMRON HBP-9030 血压监测")
        self.root.geometry(PLATFORM.window_size)
        self.root.configure(bg=self.COLORS['bg_dark'])
        self.root.resizable(True, True)
        self.root.minsize(*PLATFORM.window_min)
        
        # 树莓派默认全屏
        if PLATFORM.fullscreen:
            self.root.attributes('-fullscreen', True)
            # 按Escape退出全屏
            self.root.bind('<Escape>', lambda e: self.root.attributes('-fullscreen', False))
        
        # 数据
        self.readings: List[BloodPressureReading] = []
        self.data_queue = queue.Queue()
        self.simulation_mode = False
        self.connection_expanded = tk.BooleanVar(value=False)
        self.history_expanded = tk.BooleanVar(value=False)
        
        # 串口连接
        self.serial_conn = SerialConnection(
            on_data_received=self._on_data_received,
            on_raw_data=self._on_raw_data,
            on_status_change=self._on_status_change
        )
        
        # 模拟器
        self.simulator = Simulator(
            on_data_received=self._on_data_received,
            on_raw_data=self._on_raw_data,
            on_status_change=self._on_status_change
        )
        
        # 创建界面
        self._create_styles()
        self._create_widgets()
        
        # 更新串口列表
        self._refresh_ports()
        
        # 显示平台信息
        self._log(f"运行平台: {PLATFORM}")
        
        # 检查pyserial是否可用
        if not SERIAL_AVAILABLE:
            self._log("警告: pyserial库未安装，仅可使用模拟模式")
            self._log("安装命令: pip install pyserial")
        
        # 启动UI更新循环
        self._process_queue()
        
        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _create_styles(self):
        """创建自定义样式"""
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure('Custom.TCombobox',
                       fieldbackground=self.COLORS['bg_light'],
                       background=self.COLORS['bg_light'],
                       foreground=self.COLORS['text_primary'])
    
    def _create_widgets(self):
        """创建界面组件"""
        # 树莓派使用更紧凑的边距
        pad = 10 if PLATFORM.is_raspberry_pi else 20
        
        # ========== 主界面滚动容器（Canvas + Scrollbar）==========
        outer_frame = tk.Frame(self.root, bg=self.COLORS['bg_dark'])
        outer_frame.pack(fill=tk.BOTH, expand=True)
        
        self.main_canvas = tk.Canvas(
            outer_frame,
            bg=self.COLORS['bg_dark'],
            highlightthickness=0
        )
        self.main_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.main_scrollbar = tk.Scrollbar(
            outer_frame,
            orient=tk.VERTICAL,
            command=self.main_canvas.yview
        )
        self.main_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.main_canvas.configure(yscrollcommand=self.main_scrollbar.set)
        
        content_frame = tk.Frame(self.main_canvas, bg=self.COLORS['bg_dark'])
        content_frame.configure(padx=pad, pady=pad)
        self.content_frame = content_frame
        
        self.main_canvas_window = self.main_canvas.create_window(
            (0, 0),
            window=content_frame,
            anchor='nw'
        )
        
        def _on_frame_configure(_event):
            self.main_canvas.configure(scrollregion=self.main_canvas.bbox('all'))
        
        def _on_canvas_configure(event):
            # 让内部Frame宽度始终跟随Canvas宽度
            self.main_canvas.itemconfigure(self.main_canvas_window, width=event.width)
        
        content_frame.bind('<Configure>', _on_frame_configure)
        self.main_canvas.bind('<Configure>', _on_canvas_configure)
        
        # 绑定滚轮（Windows / Linux）
        # 说明：对 Text/Listbox/Combobox 等组件，优先让组件自身处理滚动；
        #       其余情况滚动主界面。
        self.root.bind_all('<MouseWheel>', self._on_main_mousewheel, add='+')
        self.root.bind_all('<Button-4>', self._on_main_mousewheel, add='+')
        self.root.bind_all('<Button-5>', self._on_main_mousewheel, add='+')
        
        # 默认显示最顶端
        self.root.after_idle(lambda: self.main_canvas.yview_moveto(0.0))
        
        # # 标题
        # title_label = tk.Label(
        #     main_frame,
        #     text="邵逸夫医院大运河",
        #     font=PLATFORM.get_font(15, 'bold'),
        #     fg=self.COLORS['text_primary'],
        #     bg=self.COLORS['bg_dark']
        # )
        # title_label.pack(pady=(0, pad))
        

        
        # 血压显示区
        self._create_display_frame(content_frame)

        # 连接摘要区（折叠控制区）
        self._create_connection_summary(content_frame)
        self._create_connection_frame(content_frame)
        
        # 历史记录摘要区（折叠历史记录）
        self._create_history_summary(content_frame)
        self._create_history_frame(content_frame)
        
        # 日志区
        self._create_log_frame(content_frame)

    def _on_main_mousewheel(self, event):
        """主界面滚轮滚动（Canvas 容器）"""
        # 让Text/Listbox/Combobox/Entry等控件保留自己的滚动/交互
        if isinstance(event.widget, (tk.Text, tk.Listbox, ttk.Combobox, tk.Entry)):
            return None
        
        if not hasattr(self, 'main_canvas'):
            return None
        
        # Linux: Button-4/5
        if getattr(event, 'num', None) == 4:
            self.main_canvas.yview_scroll(-1, 'units')
            return "break"
        if getattr(event, 'num', None) == 5:
            self.main_canvas.yview_scroll(1, 'units')
            return "break"
        
        # Windows: MouseWheel
        delta = getattr(event, 'delta', 0)
        if delta:
            self.main_canvas.yview_scroll(int(-1 * (delta / 120)), 'units')
            return "break"
        
        return None
    
    def _create_connection_summary(self, parent):
        """创建连接摘要区（仅显示状态点与连接按钮）"""
        frame = tk.Frame(parent, bg=self.COLORS['bg_dark'])
        frame.pack(fill=tk.X, pady=(0, 10))
        self.connection_summary_frame = frame
              
        self.summary_connect_btn = tk.Button(
            frame,
            text="连接",
            font=PLATFORM.get_font(9),
            bg=self.COLORS['success'],
            fg=self.COLORS['text_primary'],
            activebackground=self.COLORS['accent'],
            activeforeground=self.COLORS['text_primary'],
            relief=tk.FLAT,
            cursor='hand2',
            width=6,
            command=self._toggle_connection
        )
        self.summary_connect_btn.pack(side=tk.RIGHT)
        
        self.summary_indicator = tk.Canvas(
            frame,
            width=10,
            height=10,
            bg=self.COLORS['bg_dark'],
            highlightthickness=0
        )
        self.summary_indicator.pack(side=tk.RIGHT, padx=(0, 6))
        self.summary_indicator.create_oval(2, 2, 8, 8, fill=self.COLORS['danger'], outline='')

        self.toggle_connection_btn = tk.Button(
            frame,
            text="▶ 显示连接设置",
            font=PLATFORM.get_font(9),
            bg=self.COLORS['bg_dark'],
            fg=self.COLORS['text_secondary'],
            activebackground=self.COLORS['bg_dark'],
            activeforeground=self.COLORS['text_primary'],
            relief=tk.FLAT,
            cursor='hand2',
            command=self._toggle_connection_panel
        )
        self.toggle_connection_btn.pack(side=tk.LEFT)
    
    def _create_connection_frame(self, parent):
        """创建连接控制区"""
        frame = tk.Frame(parent, bg=self.COLORS['bg_medium'], padx=15, pady=15)
        self.connection_frame = frame
        
        # 第一行：端口和波特率选择
        port_frame = tk.Frame(frame, bg=self.COLORS['bg_medium'])
        port_frame.pack(fill=tk.X)
        
        tk.Label(
            port_frame,
            text="串口:",
            font=PLATFORM.get_font(11),
            fg=self.COLORS['text_primary'],
            bg=self.COLORS['bg_medium']
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(
            port_frame,
            textvariable=self.port_var,
            state='readonly',
            width=15,
            font=PLATFORM.get_mono_font(10)
        )
        self.port_combo.pack(side=tk.LEFT, padx=(0, 10))
        
        refresh_btn = tk.Button(
            port_frame,
            text="刷新",
            font=PLATFORM.get_font(10),
            bg=self.COLORS['bg_light'],
            fg=self.COLORS['text_primary'],
            activebackground=self.COLORS['accent'],
            activeforeground=self.COLORS['text_primary'],
            relief=tk.FLAT,
            cursor='hand2',
            command=self._refresh_ports
        )
        refresh_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        tk.Label(
            port_frame,
            text="波特率:",
            font=PLATFORM.get_font(11),
            fg=self.COLORS['text_primary'],
            bg=self.COLORS['bg_medium']
        ).pack(side=tk.LEFT, padx=(20, 10))
        
        self.baudrate_var = tk.StringVar(value='9600')
        baudrate_combo = ttk.Combobox(
            port_frame,
            textvariable=self.baudrate_var,
            values=['9600', '19200', '38400', '57600', '115200'],
            state='readonly',
            width=10,
            font=PLATFORM.get_mono_font(10)
        )
        baudrate_combo.pack(side=tk.LEFT, padx=(0, 20))
        
        # 连接按钮
        self.connect_btn = tk.Button(
            port_frame,
            text="连接",
            font=PLATFORM.get_font(11, 'bold'),
            bg=self.COLORS['success'],
            fg=self.COLORS['text_primary'],
            activebackground=self.COLORS['accent'],
            activeforeground=self.COLORS['text_primary'],
            relief=tk.FLAT,
            cursor='hand2',
            width=8,
            command=self._toggle_connection
        )
        self.connect_btn.pack(side=tk.LEFT)
        
        # 第二行：模拟模式和状态
        mode_frame = tk.Frame(frame, bg=self.COLORS['bg_medium'])
        mode_frame.pack(fill=tk.X, pady=(10, 0))
        
        # 模拟模式按钮
        self.sim_btn = tk.Button(
            mode_frame,
            text="启动模拟模式",
            font=PLATFORM.get_font(10),
            bg=self.COLORS['simulation'],
            fg=self.COLORS['text_primary'],
            activebackground=self.COLORS['accent'],
            activeforeground=self.COLORS['text_primary'],
            relief=tk.FLAT,
            cursor='hand2',
            command=self._toggle_simulation
        )
        self.sim_btn.pack(side=tk.LEFT, padx=(0, 15))
        
        # 模拟间隔
        tk.Label(
            mode_frame,
            text="间隔(秒):",
            font=PLATFORM.get_font(10),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        self.sim_interval_var = tk.StringVar(value='5')
        sim_interval_entry = tk.Entry(
            mode_frame,
            textvariable=self.sim_interval_var,
            width=5,
            font=PLATFORM.get_mono_font(10),
            bg=self.COLORS['bg_light'],
            fg=self.COLORS['text_primary'],
            insertbackground=self.COLORS['text_primary'],
            relief=tk.FLAT
        )
        sim_interval_entry.pack(side=tk.LEFT, padx=(0, 20))
        
        # 状态指示器
        self.status_indicator = tk.Canvas(
            mode_frame,
            width=12,
            height=12,
            bg=self.COLORS['bg_medium'],
            highlightthickness=0
        )
        self.status_indicator.pack(side=tk.LEFT)
        self.status_indicator.create_oval(2, 2, 10, 10, fill=self.COLORS['danger'], outline='')
        
        self.status_label = tk.Label(
            mode_frame,
            text="未连接",
            font=PLATFORM.get_font(10),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        )
        self.status_label.pack(side=tk.LEFT, padx=(8, 0))
    
    def _toggle_connection_panel(self):
        """切换连接控制区显示"""
        if self.connection_expanded.get():
            self.connection_frame.pack_forget()
            self.toggle_connection_btn.config(text="▶ 显示连接设置")
            self.connection_expanded.set(False)
        else:
            self.connection_frame.pack(
                fill=tk.X,
                pady=(0, 15),
                before=self.history_summary_frame
            )
            self.toggle_connection_btn.config(text="▼ 隐藏连接设置")
            self.connection_expanded.set(True)
    
    def _create_display_frame(self, parent):
        """创建血压显示区"""
        frame = tk.Frame(parent, bg=self.COLORS['bg_medium'], padx=20, pady=25)
        frame.pack(fill=tk.X, pady=(0, 15))
        
        display_container = tk.Frame(frame, bg=self.COLORS['bg_medium'])
        display_container.pack(fill=tk.X)
        
        display_container.columnconfigure(0, weight=1)
        display_container.columnconfigure(1, weight=1)
        display_container.columnconfigure(2, weight=1)
        
        # 收缩压
        sys_frame = tk.Frame(display_container, bg=self.COLORS['bg_medium'])
        sys_frame.grid(row=0, column=0, sticky='nsew', padx=10)
        
        tk.Label(
            sys_frame,
            text="收缩压",
            font=PLATFORM.get_font(14),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        ).pack()
        
        self.sys_value = tk.Label(
            sys_frame,
            text="---",
            font=PLATFORM.get_font(40, 'bold'),
            fg=self.COLORS['accent'],
            bg=self.COLORS['bg_medium']
        )
        self.sys_value.pack()
        
        tk.Label(
            sys_frame,
            text="mmHg",
            font=PLATFORM.get_font(12),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        ).pack()
        
        # 舒张压
        dia_frame = tk.Frame(display_container, bg=self.COLORS['bg_medium'])
        dia_frame.grid(row=0, column=1, sticky='nsew', padx=10)
        
        tk.Label(
            dia_frame,
            text="舒张压",
            font=PLATFORM.get_font(14),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        ).pack()
        
        self.dia_value = tk.Label(
            dia_frame,
            text="---",
            font=PLATFORM.get_font(40, 'bold'),
            fg=self.COLORS['accent_light'],
            bg=self.COLORS['bg_medium']
        )
        self.dia_value.pack()
        
        tk.Label(
            dia_frame,
            text="mmHg",
            font=PLATFORM.get_font(12),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        ).pack()
        
        # 心率
        pr_frame = tk.Frame(display_container, bg=self.COLORS['bg_medium'])
        pr_frame.grid(row=0, column=2, sticky='nsew', padx=10)
        
        tk.Label(
            pr_frame,
            text="心率",
            font=PLATFORM.get_font(14),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        ).pack()
        
        self.pr_value = tk.Label(
            pr_frame,
            text="---",
            font=PLATFORM.get_font(40, 'bold'),
            fg=self.COLORS['success'],
            bg=self.COLORS['bg_medium']
        )
        self.pr_value.pack()
        
        tk.Label(
            pr_frame,
            text="bpm",
            font=PLATFORM.get_font(12),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        ).pack()
        
        self.update_time_label = tk.Label(
            frame,
            text="等待测量数据...",
            font=PLATFORM.get_font(10),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        )
        self.update_time_label.pack(pady=(15, 0))
    
    def _create_history_frame(self, parent):
        """创建历史记录区"""
        frame = tk.Frame(parent, bg=self.COLORS['bg_medium'], padx=10, pady=6)
        self.history_frame = frame
        
        list_frame = tk.Frame(frame, bg=self.COLORS['bg_dark'])
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        
        self.history_listbox = tk.Listbox(
            list_frame,
            font=PLATFORM.get_mono_font(11),
            bg=self.COLORS['bg_dark'],
            fg=self.COLORS['text_primary'],
            selectbackground=self.COLORS['accent'],
            selectforeground=self.COLORS['text_primary'],
            highlightthickness=0,
            relief=tk.FLAT,
            yscrollcommand=scrollbar.set,
            height=5
        )
        self.history_listbox.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.history_listbox.yview)
    
    def _create_history_summary(self, parent):
        """创建历史记录摘要区（仅显示清空按钮）"""
        frame = tk.Frame(parent, bg=self.COLORS['bg_dark'])
        frame.pack(fill=tk.X)
        self.history_summary_frame = frame
        
        self.clear_history_btn = tk.Button(
            frame,
            text="清空",
            font=PLATFORM.get_font(9),
            bg=self.COLORS['bg_light'],
            fg=self.COLORS['text_secondary'],
            activebackground=self.COLORS['danger'],
            activeforeground=self.COLORS['text_primary'],
            relief=tk.FLAT,
            cursor='hand2',
            width=6,
            command=self._clear_history
        )
        self.clear_history_btn.pack(side=tk.RIGHT)
        
        self.toggle_history_btn = tk.Button(
            frame,
            text="▶ 显示历史记录",
            font=PLATFORM.get_font(9),
            bg=self.COLORS['bg_dark'],
            fg=self.COLORS['text_secondary'],
            activebackground=self.COLORS['bg_dark'],
            activeforeground=self.COLORS['text_primary'],
            relief=tk.FLAT,
            cursor='hand2',
            command=self._toggle_history
        )
        self.toggle_history_btn.pack(side=tk.LEFT)
    
    def _create_log_frame(self, parent):
        """创建日志区"""
        self.log_expanded = tk.BooleanVar(value=False)
        
        toggle_frame = tk.Frame(parent, bg=self.COLORS['bg_dark'])
        toggle_frame.pack(fill=tk.X)
        self.log_toggle_frame = toggle_frame
        
        self.toggle_log_btn = tk.Button(
            toggle_frame,
            text="▶ 显示数据日志",
            font=PLATFORM.get_font(9),
            bg=self.COLORS['bg_dark'],
            fg=self.COLORS['text_secondary'],
            activebackground=self.COLORS['bg_dark'],
            activeforeground=self.COLORS['text_primary'],
            relief=tk.FLAT,
            cursor='hand2',
            command=self._toggle_log
        )
        self.toggle_log_btn.pack(side=tk.LEFT)
        
        self.log_frame = tk.Frame(parent, bg=self.COLORS['bg_dark'])
        
        log_scrollbar = tk.Scrollbar(self.log_frame)
        log_scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        
        self.log_text = tk.Text(
            self.log_frame,
            font=PLATFORM.get_mono_font(9),
            bg=self.COLORS['bg_dark'],
            fg=self.COLORS['text_secondary'],
            height=6,
            wrap=tk.WORD,
            highlightthickness=0,
            relief=tk.FLAT,
            yscrollcommand=log_scrollbar.set
        )
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar.config(command=self.log_text.yview)
    
    def _toggle_log(self):
        """切换日志显示"""
        if self.log_expanded.get():
            self.log_frame.pack_forget()
            self.toggle_log_btn.config(text="▶ 显示数据日志")
            self.log_expanded.set(False)
        else:
            self.log_frame.pack(fill=tk.X, pady=(5, 0))
            self.toggle_log_btn.config(text="▼ 隐藏数据日志")
            self.log_expanded.set(True)
    
    def _toggle_history(self):
        """切换历史记录显示"""
        if self.history_expanded.get():
            self.history_frame.pack_forget()
            self.toggle_history_btn.config(text="▶ 显示历史记录")
            self.history_expanded.set(False)
        else:
            self.history_frame.pack(
                fill=tk.BOTH,
                expand=True,
                pady=(0, 15),
                before=self.log_toggle_frame
            )
            self.toggle_history_btn.config(text="▼ 隐藏历史记录")
            self.history_expanded.set(True)
    
    def _refresh_ports(self):
        """刷新串口列表"""
        ports = SerialConnection.get_port_info()
        port_names = [p[0] for p in ports]
        
        self.port_combo['values'] = port_names
        if port_names:
            # 默认优先选择 COM3
            default_port = 'COM3'
            if default_port in port_names:
                self.port_combo.set(default_port)
            else:
                self.port_combo.current(0)
        
        if ports:
            self._log(f"检测到 {len(ports)} 个串口:")
            for port, desc in ports:
                self._log(f"  {port}: {desc}")
        else:
            self._log("未检测到串口设备")
            if not SERIAL_AVAILABLE:
                self._log("提示: pyserial未安装，请使用模拟模式测试")
    
    def _toggle_connection(self):
        """切换连接状态"""
        if self.simulation_mode:
            messagebox.showwarning("警告", "请先停止模拟模式")
            return
            
        if self.serial_conn.is_connected:
            self.serial_conn.disconnect()
            self._update_connection_ui(False)
        else:
            port = self.port_var.get()
            baudrate = int(self.baudrate_var.get())
            
            if not port:
                messagebox.showwarning("警告", "请选择串口\n\n如果没有检测到串口，请：\n1. 检查USB线是否连接\n2. 检查设备管理器中是否有新的COM端口\n3. 可以先使用「模拟模式」测试程序")
                return
            
            if self.serial_conn.connect(port, baudrate):
                self._update_connection_ui(True)
            else:
                messagebox.showerror("连接失败", f"无法连接到 {port}\n\n可能的原因：\n1. 端口被其他程序占用\n2. 设备未正确连接\n3. 需要安装驱动程序")
    
    def _toggle_simulation(self):
        """切换模拟模式"""
        if self.serial_conn.is_connected:
            messagebox.showwarning("警告", "请先断开串口连接")
            return
            
        if self.simulation_mode:
            self.simulator.stop()
            self.simulation_mode = False
            self.sim_btn.config(text="启动模拟模式", bg=self.COLORS['simulation'])
            self._update_connection_ui(False)
        else:
            try:
                interval = float(self.sim_interval_var.get())
                if interval < 1:
                    interval = 1
                    self.sim_interval_var.set('1')
            except ValueError:
                interval = 5
                self.sim_interval_var.set('5')
            
            self.simulator.start(interval)
            self.simulation_mode = True
            self.sim_btn.config(text="停止模拟模式", bg=self.COLORS['danger'])
            self._update_connection_ui(True, is_simulation=True)
    
    def _update_connection_ui(self, connected: bool, is_simulation: bool = False):
        """更新连接状态UI"""
        if connected:
            if is_simulation:
                self.connect_btn.config(state='disabled')
                self.summary_connect_btn.config(text="模拟中", bg=self.COLORS['simulation'], state='disabled')
                self.summary_indicator.delete('all')
                self.summary_indicator.create_oval(2, 2, 8, 8, fill=self.COLORS['simulation'], outline='')
                self.status_indicator.delete('all')
                self.status_indicator.create_oval(2, 2, 10, 10, fill=self.COLORS['simulation'], outline='')
                self.status_label.config(text="模拟模式", fg=self.COLORS['simulation'])
            else:
                self.connect_btn.config(text="断开", bg=self.COLORS['danger'], state='normal')
                self.summary_connect_btn.config(text="断开", bg=self.COLORS['danger'], state='normal')
                self.summary_indicator.delete('all')
                self.summary_indicator.create_oval(2, 2, 8, 8, fill=self.COLORS['success'], outline='')
                self.sim_btn.config(state='disabled')
                self.status_indicator.delete('all')
                self.status_indicator.create_oval(2, 2, 10, 10, fill=self.COLORS['success'], outline='')
                self.status_label.config(text="已连接", fg=self.COLORS['success'])
        else:
            self.connect_btn.config(text="连接", bg=self.COLORS['success'], state='normal')
            self.summary_connect_btn.config(text="连接", bg=self.COLORS['success'], state='normal')
            self.summary_indicator.delete('all')
            self.summary_indicator.create_oval(2, 2, 8, 8, fill=self.COLORS['danger'], outline='')
            self.sim_btn.config(state='normal')
            self.status_indicator.delete('all')
            self.status_indicator.create_oval(2, 2, 10, 10, fill=self.COLORS['danger'], outline='')
            self.status_label.config(text="未连接", fg=self.COLORS['text_secondary'])
    
    def _on_data_received(self, reading: BloodPressureReading):
        """处理接收到的血压数据"""
        self.data_queue.put(('reading', reading))
    
    def _on_raw_data(self, data: bytes):
        """处理原始数据"""
        self.data_queue.put(('raw', data))
    
    def _on_status_change(self, status: str):
        """处理状态变化"""
        self.data_queue.put(('status', status))
    
    def _process_queue(self):
        """处理数据队列"""
        try:
            while True:
                msg_type, data = self.data_queue.get_nowait()
                
                if msg_type == 'reading':
                    self._update_display(data)
                elif msg_type == 'raw':
                    try:
                        decoded = data.decode('ascii', errors='replace')
                    except Exception:
                        decoded = str(data)
                    self._log(f"收到: {data.hex()} | {decoded}")
                elif msg_type == 'status':
                    self.status_label.config(text=data)
                    
        except queue.Empty:
            pass
        
        self.root.after(100, self._process_queue)
    
    def _update_display(self, reading: BloodPressureReading):
        """更新显示"""
        self.sys_value.config(text=str(reading.systolic))
        self.dia_value.config(text=str(reading.diastolic))
        self.pr_value.config(text=str(reading.pulse))
        
        self.update_time_label.config(
            text=f"最后更新: {reading.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        sys_color = self._get_bp_color(reading.systolic, 'sys')
        dia_color = self._get_bp_color(reading.diastolic, 'dia')
        self.sys_value.config(fg=sys_color)
        self.dia_value.config(fg=dia_color)
        
        self.readings.insert(0, reading)
        self.history_listbox.insert(0, str(reading))
        
        if len(self.readings) > 100:
            self.readings.pop()
            self.history_listbox.delete(tk.END)
    
    def _get_bp_color(self, value: int, bp_type: str) -> str:
        """根据血压值返回颜色"""
        if bp_type == 'sys':
            if value < 90:
                return self.COLORS['warning']
            elif value < 140:
                return self.COLORS['success']
            else:
                return self.COLORS['warning']
        else:
            if value < 60:
                return self.COLORS['warning']
            elif value < 90:
                return self.COLORS['success']
            else:
                return self.COLORS['warning']
        # if bp_type == 'sys':
        #     if value < 90:
        #         return self.COLORS['warning']
        #     elif value < 120:
        #         return self.COLORS['success']
        #     elif value < 140:
        #         return self.COLORS['warning']
        #     else:
        #         return self.COLORS['danger']
        # else:
        #     if value < 60:
        #         return self.COLORS['warning']
        #     elif value < 80:
        #         return self.COLORS['success']
        #     elif value < 90:
        #         return self.COLORS['warning']
        #     else:
        #         return self.COLORS['danger']
    
    def _clear_history(self):
        """清空历史记录"""
        self.readings.clear()
        self.history_listbox.delete(0, tk.END)
    
    def _log(self, message: str):
        """添加日志"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        
        lines = int(self.log_text.index('end-1c').split('.')[0])
        if lines > 500:
            self.log_text.delete('1.0', '100.0')
    
    def _on_closing(self):
        """关闭窗口"""
        if self.simulation_mode:
            self.simulator.stop()
        self.serial_conn.disconnect()
        self.root.destroy()
    
    def run(self):
        """运行应用"""
        self.root.mainloop()


# ============== 授权模块 ==============
class LoginDialog:
    """登录授权对话框"""
    
    # 授权密码
    PASSWORD = ""
    
    # 颜色主题
    COLORS = {
        'bg_dark': '#1a1a2e',
        'bg_medium': '#16213e',
        'bg_light': '#0f3460',
        'accent': '#e94560',
        'text_primary': '#ffffff',
        'text_secondary': '#a0a0a0',
        'success': '#4ecca3',
        'danger': '#ff6b6b',
    }
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("OMRON HBP-9030 - 授权验证")
        self.root.geometry("400x280")
        self.root.configure(bg=self.COLORS['bg_dark'])
        self.root.resizable(False, False)
        
        # 居中显示
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
        self.authorized = False
        self.attempts = 0
        self.max_attempts = 5
        
        self._create_widgets()
        
        # 绑定回车键
        self.root.bind('<Return>', lambda e: self._verify())
        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # 聚焦到密码输入框
        self.password_entry.focus_set()
    
    def _create_widgets(self):
        """创建界面组件"""
        main_frame = tk.Frame(self.root, bg=self.COLORS['bg_dark'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # 标题
        tk.Label(
            main_frame,
            text="🔒 授权验证",
            font=PLATFORM.get_font(20, 'bold'),
            fg=self.COLORS['text_primary'],
            bg=self.COLORS['bg_dark']
        ).pack(pady=(0, 10))
        
        # 副标题
        tk.Label(
            main_frame,
            text="OMRON HBP-9030 血压监测程序",
            font=PLATFORM.get_font(11),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_dark']
        ).pack(pady=(0, 25))
        
        # 密码输入区
        input_frame = tk.Frame(main_frame, bg=self.COLORS['bg_medium'], padx=20, pady=20)
        input_frame.pack(fill=tk.X)
        
        tk.Label(
            input_frame,
            text="请输入授权密码：",
            font=PLATFORM.get_font(11),
            fg=self.COLORS['text_primary'],
            bg=self.COLORS['bg_medium']
        ).pack(anchor='w', pady=(0, 8))
        
        self.password_var = tk.StringVar()
        self.password_entry = tk.Entry(
            input_frame,
            textvariable=self.password_var,
            show="●",
            font=PLATFORM.get_mono_font(14),
            bg=self.COLORS['bg_light'],
            fg=self.COLORS['text_primary'],
            insertbackground=self.COLORS['text_primary'],
            relief=tk.FLAT,
            width=25
        )
        self.password_entry.pack(fill=tk.X, ipady=8)
        
        # 错误提示
        self.error_label = tk.Label(
            input_frame,
            text="",
            font=PLATFORM.get_font(9),
            fg=self.COLORS['danger'],
            bg=self.COLORS['bg_medium']
        )
        self.error_label.pack(anchor='w', pady=(8, 0))
        
        # 按钮区
        btn_frame = tk.Frame(main_frame, bg=self.COLORS['bg_dark'])
        btn_frame.pack(fill=tk.X, pady=(20, 0))
        
        self.login_btn = tk.Button(
            btn_frame,
            text="验证并进入",
            font=PLATFORM.get_font(11, 'bold'),
            bg=self.COLORS['success'],
            fg=self.COLORS['text_primary'],
            activebackground=self.COLORS['accent'],
            activeforeground=self.COLORS['text_primary'],
            relief=tk.FLAT,
            cursor='hand2',
            width=15,
            command=self._verify
        )
        self.login_btn.pack(side=tk.LEFT, expand=True)
        
        tk.Button(
            btn_frame,
            text="退出",
            font=PLATFORM.get_font(11),
            bg=self.COLORS['bg_light'],
            fg=self.COLORS['text_secondary'],
            activebackground=self.COLORS['danger'],
            activeforeground=self.COLORS['text_primary'],
            relief=tk.FLAT,
            cursor='hand2',
            width=10,
            command=self._on_close
        ).pack(side=tk.RIGHT, expand=True)
    
    def _verify(self):
        """验证密码"""
        password = self.password_var.get()
        
        if password == self.PASSWORD:
            self.authorized = True
            logger.info("授权验证成功")
            self.root.destroy()
        else:
            self.attempts += 1
            remaining = self.max_attempts - self.attempts
            
            if remaining <= 0:
                logger.warning("授权验证失败次数过多，程序退出")
                messagebox.showerror("授权失败", "密码错误次数过多，程序将退出。")
                self.root.destroy()
            else:
                self.error_label.config(text=f"密码错误！剩余尝试次数：{remaining}")
                self.password_var.set("")
                self.password_entry.focus_set()
                logger.warning(f"授权验证失败，剩余尝试次数：{remaining}")
    
    def _on_close(self):
        """关闭窗口"""
        self.authorized = False
        self.root.destroy()
    
    def run(self) -> bool:
        """运行登录对话框，返回是否授权成功"""
        self.root.mainloop()
        return self.authorized


def main():
    """主函数"""
    logger.info("启动 OMRON HBP-9030 血压监测程序")
    
    # ========== 授权验证 ==========
    login = LoginDialog()
    if not login.run():
        logger.info("用户取消授权或验证失败，程序退出")
        return
    
    # ========== 启动主程序 ==========
    # 检查环境
    if not SERIAL_AVAILABLE:
        logger.warning("pyserial库未安装，将只能使用模拟模式")
    
    app = BloodPressureMonitorGUI()
    app.run()


if __name__ == '__main__':
    main()
