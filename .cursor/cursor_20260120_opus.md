# 欧姆龙血压计数据传输
_Exported on 1/20/2026 at 12:21:46 GMT+8 from Cursor (2.2.44)_

---

**User**

我有一个omron血压计，型号是HBP-9030，输出12v-3.5A，配备了 USB 接口。我想通过接口接到一个电脑上，让电脑也可以在屏幕上显示测得的血压和心率等，测量完成后立即传输结果。使用 Python 写个程序，能实现该功能

---

**Cursor**

我来帮你了解欧姆龙HBP-9030血压计的通信接口和协议，以便设计Python程序。让我先搜索一些相关信息。

让我尝试用其他关键词搜索：

根据搜索结果，我找到了关于HBP-9030血压计USB通信的一些重要信息：

## 已知信息

1. **USB数据传输功能**：HBP-9030 确实支持通过USB将测量结果传输给电脑
2. **USB接口类型**：使用USB 2.0，机身背面有USB-B接口
3. **传输格式**：设备有5种不同的传输格式（格式1-5），可在设备的功能选择模式中设置（项号32：USB通信输出）
4. **数据内容**：包含日期时间、收缩压(SYS)、舒张压(DIA)、脉搏率(PR)、设备ID等信息
5. **驱动方式**：可能被识别为USB虚拟串口（USB-CDC）

在我为你创建详细的实现计划之前，我需要确认几个关键问题：

感谢你的回答！根据你的需求，我现在可以制定一个详细的实现计划。

---

**User**

Implement the plan as specified, it is attached for your reference. Do NOT edit the plan file itself.

To-do's from the plan have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the to-dos.

---

**Cursor**

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OMRON HBP-9030 血压计数据监测程序
通过USB串口读取血压计数据并在图形界面显示
"""

import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import threading
import re
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, List, Callable
import queue

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bp_monitor.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


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


class DataParser:
    """
    HBP-9030 数据解析器
    支持多种可能的数据格式
    """
    
    @staticmethod
    def parse(data: bytes) -> Optional[BloodPressureReading]:
        """
        尝试解析血压数据
        支持多种格式的自动识别
        """
        try:
            # 尝试不同的编码方式解码
            for encoding in ['ascii', 'utf-8', 'latin-1']:
                try:
                    text = data.decode(encoding).strip()
                    break
                except UnicodeDecodeError:
                    continue
            else:
                text = data.decode('ascii', errors='ignore').strip()
            
            if not text:
                return None
                
            logger.debug(f"接收原始数据: {repr(text)}")
            logger.debug(f"十六进制: {data.hex()}")
            
            # 尝试多种格式解析
            result = (
                DataParser._parse_format_csv(text) or
                DataParser._parse_format_space(text) or
                DataParser._parse_format_labeled(text) or
                DataParser._parse_format_numeric(text) or
                DataParser._parse_format_bytes(data)
            )
            
            if result:
                result.raw_data = text
                logger.info(f"解析成功: SYS={result.systolic}, DIA={result.diastolic}, PR={result.pulse}")
            
            return result
            
        except Exception as e:
            logger.error(f"解析数据时出错: {e}")
            return None
    
    @staticmethod
    def _parse_format_csv(text: str) -> Optional[BloodPressureReading]:
        """解析CSV格式: 日期,时间,SYS,DIA,PR 或类似格式"""
        try:
            # 匹配逗号分隔的数字序列
            parts = text.split(',')
            if len(parts) >= 3:
                # 查找三个连续的数字（可能是SYS, DIA, PR）
                numbers = []
                for p in parts:
                    p = p.strip()
                    if p.isdigit():
                        numbers.append(int(p))
                
                # 寻找合理的血压值范围
                for i in range(len(numbers) - 2):
                    sys_val, dia_val, pr_val = numbers[i], numbers[i+1], numbers[i+2]
                    if 60 <= sys_val <= 300 and 30 <= dia_val <= 200 and 30 <= pr_val <= 200:
                        if sys_val > dia_val:  # 收缩压应大于舒张压
                            return BloodPressureReading(
                                systolic=sys_val,
                                diastolic=dia_val,
                                pulse=pr_val,
                                timestamp=datetime.now()
                            )
        except Exception:
            pass
        return None
    
    @staticmethod
    def _parse_format_space(text: str) -> Optional[BloodPressureReading]:
        """解析空格分隔格式"""
        try:
            parts = text.split()
            numbers = [int(p) for p in parts if p.isdigit()]
            
            for i in range(len(numbers) - 2):
                sys_val, dia_val, pr_val = numbers[i], numbers[i+1], numbers[i+2]
                if 60 <= sys_val <= 300 and 30 <= dia_val <= 200 and 30 <= pr_val <= 200:
                    if sys_val > dia_val:
                        return BloodPressureReading(
                            systolic=sys_val,
                            diastolic=dia_val,
                            pulse=pr_val,
                            timestamp=datetime.now()
                        )
        except Exception:
            pass
        return None
    
    @staticmethod
    def _parse_format_labeled(text: str) -> Optional[BloodPressureReading]:
        """解析带标签格式: SYS:120 DIA:80 PR:72 等"""
        try:
            # 查找 SYS/收缩压 值
            sys_match = re.search(r'(?:SYS|sys|收缩|高压)[:\s=]*(\d+)', text)
            dia_match = re.search(r'(?:DIA|dia|舒张|低压)[:\s=]*(\d+)', text)
            pr_match = re.search(r'(?:PR|pr|HR|hr|脉搏|心率|PULSE|pulse)[:\s=]*(\d+)', text)
            
            if sys_match and dia_match and pr_match:
                return BloodPressureReading(
                    systolic=int(sys_match.group(1)),
                    diastolic=int(dia_match.group(1)),
                    pulse=int(pr_match.group(1)),
                    timestamp=datetime.now()
                )
            
            # 另一种格式: 120/80 72
            bp_match = re.search(r'(\d{2,3})\s*/\s*(\d{2,3})\s+(\d{2,3})', text)
            if bp_match:
                return BloodPressureReading(
                    systolic=int(bp_match.group(1)),
                    diastolic=int(bp_match.group(2)),
                    pulse=int(bp_match.group(3)),
                    timestamp=datetime.now()
                )
        except Exception:
            pass
        return None
    
    @staticmethod
    def _parse_format_numeric(text: str) -> Optional[BloodPressureReading]:
        """解析纯数字格式，如连续的数字字符串"""
        try:
            # 提取所有数字
            numbers = re.findall(r'\d+', text)
            if len(numbers) >= 3:
                # 查找合理的血压值组合
                for i in range(len(numbers) - 2):
                    sys_val = int(numbers[i])
                    dia_val = int(numbers[i+1])
                    pr_val = int(numbers[i+2])
                    
                    if 60 <= sys_val <= 300 and 30 <= dia_val <= 200 and 30 <= pr_val <= 200:
                        if sys_val > dia_val:
                            return BloodPressureReading(
                                systolic=sys_val,
                                diastolic=dia_val,
                                pulse=pr_val,
                                timestamp=datetime.now()
                            )
        except Exception:
            pass
        return None
    
    @staticmethod
    def _parse_format_bytes(data: bytes) -> Optional[BloodPressureReading]:
        """解析二进制格式，假设固定位置存储数值"""
        try:
            if len(data) >= 6:
                # 尝试多种字节位置组合
                # 假设数据可能是: [header...] [SYS_H] [SYS_L] [DIA_H] [DIA_L] [PR_H] [PR_L] 或单字节
                for offset in range(len(data) - 2):
                    sys_val = data[offset]
                    dia_val = data[offset + 1]
                    pr_val = data[offset + 2]
                    
                    if 60 <= sys_val <= 250 and 30 <= dia_val <= 150 and 30 <= pr_val <= 180:
                        if sys_val > dia_val:
                            return BloodPressureReading(
                                systolic=sys_val,
                                diastolic=dia_val,
                                pulse=pr_val,
                                timestamp=datetime.now()
                            )
        except Exception:
            pass
        return None


class SerialConnection:
    """串口连接管理器"""
    
    def __init__(self, on_data_received: Callable[[BloodPressureReading], None] = None,
                 on_raw_data: Callable[[bytes], None] = None,
                 on_status_change: Callable[[str], None] = None):
        self.serial_port: Optional[serial.Serial] = None
        self.is_running = False
        self.read_thread: Optional[threading.Thread] = None
        self.on_data_received = on_data_received
        self.on_raw_data = on_raw_data
        self.on_status_change = on_status_change
        
    @staticmethod
    def list_ports() -> List[str]:
        """获取可用串口列表"""
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]
    
    @staticmethod
    def get_port_info() -> List[tuple]:
        """获取串口详细信息"""
        ports = serial.tools.list_ports.comports()
        return [(port.device, port.description) for port in ports]
    
    def connect(self, port: str, baudrate: int = 9600, timeout: float = 1.0) -> bool:
        """连接到串口"""
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
            logger.error(f"连接失败: {e}")
            self._notify_status(f"连接失败: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        self.stop_reading()
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
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
        
        while self.is_running and self.serial_port and self.serial_port.is_open:
            try:
                if self.serial_port.in_waiting > 0:
                    data = self.serial_port.read(self.serial_port.in_waiting)
                    buffer += data
                    
                    # 通知原始数据
                    if self.on_raw_data:
                        self.on_raw_data(data)
                    
                    # 检查是否有完整的数据行（以换行符结尾）
                    while b'\r' in buffer or b'\n' in buffer:
                        # 找到行结束位置
                        end_pos = -1
                        for i, b in enumerate(buffer):
                            if b in (0x0D, 0x0A):  # CR or LF
                                end_pos = i
                                break
                        
                        if end_pos >= 0:
                            line = buffer[:end_pos]
                            buffer = buffer[end_pos + 1:]
                            
                            # 跳过空行
                            if line.strip():
                                self._process_data(line)
                    
                    # 如果缓冲区过长但没有行结束符，也尝试解析
                    if len(buffer) > 256:
                        self._process_data(buffer)
                        buffer = b''
                        
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
    }
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("OMRON HBP-9030 血压监测")
        self.root.geometry("650x700")
        self.root.configure(bg=self.COLORS['bg_dark'])
        self.root.resizable(True, True)
        self.root.minsize(550, 600)
        
        # 数据
        self.readings: List[BloodPressureReading] = []
        self.data_queue = queue.Queue()
        
        # 串口连接
        self.serial_conn = SerialConnection(
            on_data_received=self._on_data_received,
            on_raw_data=self._on_raw_data,
            on_status_change=self._on_status_change
        )
        
        # 创建界面
        self._create_styles()
        self._create_widgets()
        
        # 更新串口列表
        self._refresh_ports()
        
        # 启动UI更新循环
        self._process_queue()
        
        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _create_styles(self):
        """创建自定义样式"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # 配置Combobox样式
        style.configure('Custom.TCombobox',
                       fieldbackground=self.COLORS['bg_light'],
                       background=self.COLORS['bg_light'],
                       foreground=self.COLORS['text_primary'])
    
    def _create_widgets(self):
        """创建界面组件"""
        # 主容器
        main_frame = tk.Frame(self.root, bg=self.COLORS['bg_dark'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 标题
        title_label = tk.Label(
            main_frame,
            text="OMRON HBP-9030 血压监测",
            font=('Microsoft YaHei UI', 24, 'bold'),
            fg=self.COLORS['text_primary'],
            bg=self.COLORS['bg_dark']
        )
        title_label.pack(pady=(0, 20))
        
        # 连接控制区
        self._create_connection_frame(main_frame)
        
        # 血压显示区
        self._create_display_frame(main_frame)
        
        # 历史记录区
        self._create_history_frame(main_frame)
        
        # 日志区（可折叠）
        self._create_log_frame(main_frame)
    
    def _create_connection_frame(self, parent):
        """创建连接控制区"""
        frame = tk.Frame(parent, bg=self.COLORS['bg_medium'], padx=15, pady=15)
        frame.pack(fill=tk.X, pady=(0, 15))
        
        # 端口选择
        port_frame = tk.Frame(frame, bg=self.COLORS['bg_medium'])
        port_frame.pack(fill=tk.X)
        
        tk.Label(
            port_frame,
            text="串口:",
            font=('Microsoft YaHei UI', 11),
            fg=self.COLORS['text_primary'],
            bg=self.COLORS['bg_medium']
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(
            port_frame,
            textvariable=self.port_var,
            state='readonly',
            width=15,
            font=('Consolas', 10)
        )
        self.port_combo.pack(side=tk.LEFT, padx=(0, 10))
        
        # 刷新按钮
        refresh_btn = tk.Button(
            port_frame,
            text="刷新",
            font=('Microsoft YaHei UI', 10),
            bg=self.COLORS['bg_light'],
            fg=self.COLORS['text_primary'],
            activebackground=self.COLORS['accent'],
            activeforeground=self.COLORS['text_primary'],
            relief=tk.FLAT,
            cursor='hand2',
            command=self._refresh_ports
        )
        refresh_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 波特率选择
        tk.Label(
            port_frame,
            text="波特率:",
            font=('Microsoft YaHei UI', 11),
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
            font=('Consolas', 10)
        )
        baudrate_combo.pack(side=tk.LEFT, padx=(0, 20))
        
        # 连接按钮
        self.connect_btn = tk.Button(
            port_frame,
            text="连接",
            font=('Microsoft YaHei UI', 11, 'bold'),
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
        
        # 状态显示
        status_frame = tk.Frame(frame, bg=self.COLORS['bg_medium'])
        status_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.status_indicator = tk.Canvas(
            status_frame,
            width=12,
            height=12,
            bg=self.COLORS['bg_medium'],
            highlightthickness=0
        )
        self.status_indicator.pack(side=tk.LEFT)
        self.status_indicator.create_oval(2, 2, 10, 10, fill=self.COLORS['danger'], outline='')
        
        self.status_label = tk.Label(
            status_frame,
            text="未连接",
            font=('Microsoft YaHei UI', 10),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        )
        self.status_label.pack(side=tk.LEFT, padx=(8, 0))
    
    def _create_display_frame(self, parent):
        """创建血压显示区"""
        frame = tk.Frame(parent, bg=self.COLORS['bg_medium'], padx=20, pady=25)
        frame.pack(fill=tk.X, pady=(0, 15))
        
        # 三列显示
        display_container = tk.Frame(frame, bg=self.COLORS['bg_medium'])
        display_container.pack(fill=tk.X)
        
        # 配置列权重使其均匀分布
        display_container.columnconfigure(0, weight=1)
        display_container.columnconfigure(1, weight=1)
        display_container.columnconfigure(2, weight=1)
        
        # 收缩压
        sys_frame = tk.Frame(display_container, bg=self.COLORS['bg_medium'])
        sys_frame.grid(row=0, column=0, sticky='nsew', padx=10)
        
        tk.Label(
            sys_frame,
            text="收缩压",
            font=('Microsoft YaHei UI', 14),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        ).pack()
        
        self.sys_value = tk.Label(
            sys_frame,
            text="---",
            font=('Segoe UI', 56, 'bold'),
            fg=self.COLORS['accent'],
            bg=self.COLORS['bg_medium']
        )
        self.sys_value.pack()
        
        tk.Label(
            sys_frame,
            text="mmHg",
            font=('Microsoft YaHei UI', 12),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        ).pack()
        
        # 舒张压
        dia_frame = tk.Frame(display_container, bg=self.COLORS['bg_medium'])
        dia_frame.grid(row=0, column=1, sticky='nsew', padx=10)
        
        tk.Label(
            dia_frame,
            text="舒张压",
            font=('Microsoft YaHei UI', 14),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        ).pack()
        
        self.dia_value = tk.Label(
            dia_frame,
            text="---",
            font=('Segoe UI', 56, 'bold'),
            fg=self.COLORS['accent_light'],
            bg=self.COLORS['bg_medium']
        )
        self.dia_value.pack()
        
        tk.Label(
            dia_frame,
            text="mmHg",
            font=('Microsoft YaHei UI', 12),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        ).pack()
        
        # 心率
        pr_frame = tk.Frame(display_container, bg=self.COLORS['bg_medium'])
        pr_frame.grid(row=0, column=2, sticky='nsew', padx=10)
        
        tk.Label(
            pr_frame,
            text="心率",
            font=('Microsoft YaHei UI', 14),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        ).pack()
        
        self.pr_value = tk.Label(
            pr_frame,
            text="---",
            font=('Segoe UI', 56, 'bold'),
            fg=self.COLORS['success'],
            bg=self.COLORS['bg_medium']
        )
        self.pr_value.pack()
        
        tk.Label(
            pr_frame,
            text="bpm",
            font=('Microsoft YaHei UI', 12),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        ).pack()
        
        # 最后更新时间
        self.update_time_label = tk.Label(
            frame,
            text="等待测量数据...",
            font=('Microsoft YaHei UI', 10),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        )
        self.update_time_label.pack(pady=(15, 0))
    
    def _create_history_frame(self, parent):
        """创建历史记录区"""
        frame = tk.Frame(parent, bg=self.COLORS['bg_medium'], padx=15, pady=15)
        frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # 标题栏
        header_frame = tk.Frame(frame, bg=self.COLORS['bg_medium'])
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(
            header_frame,
            text="历史记录",
            font=('Microsoft YaHei UI', 12, 'bold'),
            fg=self.COLORS['text_primary'],
            bg=self.COLORS['bg_medium']
        ).pack(side=tk.LEFT)
        
        clear_btn = tk.Button(
            header_frame,
            text="清空",
            font=('Microsoft YaHei UI', 9),
            bg=self.COLORS['bg_light'],
            fg=self.COLORS['text_secondary'],
            activebackground=self.COLORS['danger'],
            activeforeground=self.COLORS['text_primary'],
            relief=tk.FLAT,
            cursor='hand2',
            command=self._clear_history
        )
        clear_btn.pack(side=tk.RIGHT)
        
        # 历史列表
        list_frame = tk.Frame(frame, bg=self.COLORS['bg_dark'])
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建Listbox和滚动条
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.history_listbox = tk.Listbox(
            list_frame,
            font=('Consolas', 11),
            bg=self.COLORS['bg_dark'],
            fg=self.COLORS['text_primary'],
            selectbackground=self.COLORS['accent'],
            selectforeground=self.COLORS['text_primary'],
            highlightthickness=0,
            relief=tk.FLAT,
            yscrollcommand=scrollbar.set
        )
        self.history_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.history_listbox.yview)
    
    def _create_log_frame(self, parent):
        """创建日志区（用于调试）"""
        # 折叠按钮
        self.log_expanded = tk.BooleanVar(value=False)
        
        toggle_frame = tk.Frame(parent, bg=self.COLORS['bg_dark'])
        toggle_frame.pack(fill=tk.X)
        
        self.toggle_log_btn = tk.Button(
            toggle_frame,
            text="▶ 显示原始数据日志",
            font=('Microsoft YaHei UI', 9),
            bg=self.COLORS['bg_dark'],
            fg=self.COLORS['text_secondary'],
            activebackground=self.COLORS['bg_dark'],
            activeforeground=self.COLORS['text_primary'],
            relief=tk.FLAT,
            cursor='hand2',
            command=self._toggle_log
        )
        self.toggle_log_btn.pack(anchor='w')
        
        # 日志文本框
        self.log_frame = tk.Frame(parent, bg=self.COLORS['bg_dark'])
        
        log_scrollbar = tk.Scrollbar(self.log_frame)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.log_text = tk.Text(
            self.log_frame,
            font=('Consolas', 9),
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
            self.toggle_log_btn.config(text="▶ 显示原始数据日志")
            self.log_expanded.set(False)
        else:
            self.log_frame.pack(fill=tk.X, pady=(5, 0))
            self.toggle_log_btn.config(text="▼ 隐藏原始数据日志")
            self.log_expanded.set(True)
    
    def _refresh_ports(self):
        """刷新串口列表"""
        ports = SerialConnection.get_port_info()
        port_names = [p[0] for p in ports]
        
        self.port_combo['values'] = port_names
        if port_names:
            self.port_combo.current(0)
            
        # 在日志中显示端口信息
        self._log(f"检测到 {len(ports)} 个串口:")
        for port, desc in ports:
            self._log(f"  {port}: {desc}")
    
    def _toggle_connection(self):
        """切换连接状态"""
        if self.serial_conn.is_connected:
            self.serial_conn.disconnect()
            self._update_connection_ui(False)
        else:
            port = self.port_var.get()
            baudrate = int(self.baudrate_var.get())
            
            if not port:
                messagebox.showwarning("警告", "请选择串口")
                return
            
            if self.serial_conn.connect(port, baudrate):
                self._update_connection_ui(True)
            else:
                messagebox.showerror("错误", f"无法连接到 {port}")
    
    def _update_connection_ui(self, connected: bool):
        """更新连接状态UI"""
        if connected:
            self.connect_btn.config(text="断开", bg=self.COLORS['danger'])
            self.status_indicator.delete('all')
            self.status_indicator.create_oval(2, 2, 10, 10, fill=self.COLORS['success'], outline='')
            self.status_label.config(text="已连接", fg=self.COLORS['success'])
        else:
            self.connect_btn.config(text="连接", bg=self.COLORS['success'])
            self.status_indicator.delete('all')
            self.status_indicator.create_oval(2, 2, 10, 10, fill=self.COLORS['danger'], outline='')
            self.status_label.config(text="未连接", fg=self.COLORS['text_secondary'])
    
    def _on_data_received(self, reading: BloodPressureReading):
        """处理接收到的血压数据（在工作线程中调用）"""
        self.data_queue.put(('reading', reading))
    
    def _on_raw_data(self, data: bytes):
        """处理原始数据（在工作线程中调用）"""
        self.data_queue.put(('raw', data))
    
    def _on_status_change(self, status: str):
        """处理状态变化（在工作线程中调用）"""
        self.data_queue.put(('status', status))
    
    def _process_queue(self):
        """处理数据队列（在主线程中）"""
        try:
            while True:
                msg_type, data = self.data_queue.get_nowait()
                
                if msg_type == 'reading':
                    self._update_display(data)
                elif msg_type == 'raw':
                    self._log(f"收到: {data.hex()} | {data.decode('ascii', errors='replace')}")
                elif msg_type == 'status':
                    self.status_label.config(text=data)
                    
        except queue.Empty:
            pass
        
        # 继续定时检查队列
        self.root.after(100, self._process_queue)
    
    def _update_display(self, reading: BloodPressureReading):
        """更新显示"""
        # 更新数值显示
        self.sys_value.config(text=str(reading.systolic))
        self.dia_value.config(text=str(reading.diastolic))
        self.pr_value.config(text=str(reading.pulse))
        
        # 更新时间
        self.update_time_label.config(
            text=f"最后更新: {reading.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        # 根据血压值设置颜色
        sys_color = self._get_bp_color(reading.systolic, 'sys')
        dia_color = self._get_bp_color(reading.diastolic, 'dia')
        self.sys_value.config(fg=sys_color)
        self.dia_value.config(fg=dia_color)
        
        # 添加到历史记录
        self.readings.insert(0, reading)
        self.history_listbox.insert(0, str(reading))
        
        # 保持历史记录不超过100条
        if len(self.readings) > 100:
            self.readings.pop()
            self.history_listbox.delete(tk.END)
    
    def _get_bp_color(self, value: int, bp_type: str) -> str:
        """根据血压值返回颜色"""
        if bp_type == 'sys':
            if value < 90:
                return self.COLORS['warning']  # 低血压
            elif value < 120:
                return self.COLORS['success']  # 正常
            elif value < 140:
                return self.COLORS['warning']  # 正常高值
            else:
                return self.COLORS['danger']   # 高血压
        else:  # dia
            if value < 60:
                return self.COLORS['warning']  # 低血压
            elif value < 80:
                return self.COLORS['success']  # 正常
            elif value < 90:
                return self.COLORS['warning']  # 正常高值
            else:
                return self.COLORS['danger']   # 高血压
    
    def _clear_history(self):
        """清空历史记录"""
        self.readings.clear()
        self.history_listbox.delete(0, tk.END)
    
    def _log(self, message: str):
        """添加日志"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        
        # 限制日志行数
        lines = int(self.log_text.index('end-1c').split('.')[0])
        if lines > 500:
            self.log_text.delete('1.0', '100.0')
    
    def _on_closing(self):
        """关闭窗口"""
        self.serial_conn.disconnect()
        self.root.destroy()
    
    def run(self):
        """运行应用"""
        self.root.mainloop()


def main():
    """主函数"""
    logger.info("启动 OMRON HBP-9030 血压监测程序")
    app = BloodPressureMonitorGUI()
    app.run()


if __name__ == '__main__':
    main()

```

```pip-requirements
# OMRON HBP-9030 血压监测程序依赖
# Python 3.7+ required

# 串口通信
pyserial>=3.5

```

已完成所有任务！我为你创建了以下文件：

## 创建的文件

1. **`bp_monitor.py`** - 主程序，包含：
   - **串口通信模块** (`SerialConnection`): 自动扫描COM端口、后台线程监听数据
   - **数据解析模块** (`DataParser`): 支持多种数据格式自动识别（CSV、空格分隔、带标签、纯数字、二进制）
   - **图形界面** (`BloodPressureMonitorGUI`): 现代深色主题界面，大字体显示血压心率

2. **`requirements.txt`** - 依赖文件

## 使用方法

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 将HBP-9030通过USB连接到电脑

3. 运行程序：
```bash
python bp_monitor.py
```

4. 在程序界面中选择对应的COM端口，点击"连接"

5. 在血压计上进行测量，完成后数据会自动显示在屏幕上

## 程序特点

- **自动端口扫描**: 自动检测可用的串口
- **多格式解析**: 自动尝试多种数据格式，适应不同的设备设置
- **血压颜色提示**: 根据血压值自动变色（正常绿色、偏高黄色、高血压红色）
- **历史记录**: 保存最近100条测量记录
- **原始数据日志**: 可展开查看原始通信数据，便于调试
- **日志文件**: 自动生成 `bp_monitor.log` 记录所有通信数据

## 注意事项

- 首次连接时，请在Windows设备管理器中确认血压计是否被识别为COM端口
- 如果没有自动识别，可能需要安装USB-CDC驱动
- 默认波特率为9600，如果无法接收数据可尝试其他波特率
- 程序会自动记录所有原始数据到日志，如果解析失败可根据日志调整

```shellscript
pip install -r requirements.txt
```

```shellscript
python bp_monitor.py
```

---

**User**

我现在手头没有omron这个机器，而程序最终需要安装在医院的电脑上，这个电脑可能没有任何python开发环境等。我希望尽量一次通过，应该怎么打磨程序？如果我要远程指导一个从来没用过python和命令行的人配置好这个程序，我应该怎么做，或者可不可以优化程序让这个过程更简单？

---

**Cursor**

这是一个很好的问题！针对你的情况，我建议：

1. **将程序打包成独立的 `.exe` 文件** - 不需要安装Python，双击即可运行
2. **添加模拟模式** - 让你可以在没有设备的情况下测试界面和功能
3. **改进错误处理和提示** - 让程序更健壮，提示更友好

让我来优化程序并创建打包脚本：

现在我来对程序进行全面优化，添加模拟模式、改进错误处理，并创建打包脚本。

```python
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
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import re
import random
import time
import os
import sys
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
    支持多种可能的数据格式
    """
    
    @staticmethod
    def parse(data: bytes) -> Optional[BloodPressureReading]:
        """
        尝试解析血压数据
        支持多种格式的自动识别
        """
        try:
            # 尝试不同的编码方式解码
            text = ""
            for encoding in ['ascii', 'utf-8', 'latin-1', 'gbk']:
                try:
                    text = data.decode(encoding).strip()
                    break
                except (UnicodeDecodeError, LookupError):
                    continue
            
            if not text:
                text = data.decode('ascii', errors='ignore').strip()
            
            if not text:
                return None
                
            logger.debug(f"接收原始数据: {repr(text)}")
            logger.debug(f"十六进制: {data.hex()}")
            
            # 尝试多种格式解析
            result = (
                DataParser._parse_format_csv(text) or
                DataParser._parse_format_space(text) or
                DataParser._parse_format_labeled(text) or
                DataParser._parse_format_numeric(text) or
                DataParser._parse_format_bytes(data)
            )
            
            if result:
                result.raw_data = text
                logger.info(f"解析成功: SYS={result.systolic}, DIA={result.diastolic}, PR={result.pulse}")
            
            return result
            
        except Exception as e:
            logger.error(f"解析数据时出错: {e}")
            return None
    
    @staticmethod
    def _parse_format_csv(text: str) -> Optional[BloodPressureReading]:
        """解析CSV格式: 日期,时间,SYS,DIA,PR 或类似格式"""
        try:
            parts = text.split(',')
            if len(parts) >= 3:
                numbers = []
                for p in parts:
                    p = p.strip()
                    if p.isdigit():
                        numbers.append(int(p))
                
                for i in range(len(numbers) - 2):
                    sys_val, dia_val, pr_val = numbers[i], numbers[i+1], numbers[i+2]
                    if 60 <= sys_val <= 300 and 30 <= dia_val <= 200 and 30 <= pr_val <= 200:
                        if sys_val > dia_val:
                            return BloodPressureReading(
                                systolic=sys_val,
                                diastolic=dia_val,
                                pulse=pr_val,
                                timestamp=datetime.now()
                            )
        except Exception:
            pass
        return None
    
    @staticmethod
    def _parse_format_space(text: str) -> Optional[BloodPressureReading]:
        """解析空格分隔格式"""
        try:
            parts = text.split()
            numbers = [int(p) for p in parts if p.isdigit()]
            
            for i in range(len(numbers) - 2):
                sys_val, dia_val, pr_val = numbers[i], numbers[i+1], numbers[i+2]
                if 60 <= sys_val <= 300 and 30 <= dia_val <= 200 and 30 <= pr_val <= 200:
                    if sys_val > dia_val:
                        return BloodPressureReading(
                            systolic=sys_val,
                            diastolic=dia_val,
                            pulse=pr_val,
                            timestamp=datetime.now()
                        )
        except Exception:
            pass
        return None
    
    @staticmethod
    def _parse_format_labeled(text: str) -> Optional[BloodPressureReading]:
        """解析带标签格式: SYS:120 DIA:80 PR:72 等"""
        try:
            sys_match = re.search(r'(?:SYS|sys|收缩|高压)[:\s=]*(\d+)', text)
            dia_match = re.search(r'(?:DIA|dia|舒张|低压)[:\s=]*(\d+)', text)
            pr_match = re.search(r'(?:PR|pr|HR|hr|脉搏|心率|PULSE|pulse)[:\s=]*(\d+)', text)
            
            if sys_match and dia_match and pr_match:
                return BloodPressureReading(
                    systolic=int(sys_match.group(1)),
                    diastolic=int(dia_match.group(1)),
                    pulse=int(pr_match.group(1)),
                    timestamp=datetime.now()
                )
            
            bp_match = re.search(r'(\d{2,3})\s*/\s*(\d{2,3})\s+(\d{2,3})', text)
            if bp_match:
                return BloodPressureReading(
                    systolic=int(bp_match.group(1)),
                    diastolic=int(bp_match.group(2)),
                    pulse=int(bp_match.group(3)),
                    timestamp=datetime.now()
                )
        except Exception:
            pass
        return None
    
    @staticmethod
    def _parse_format_numeric(text: str) -> Optional[BloodPressureReading]:
        """解析纯数字格式"""
        try:
            numbers = re.findall(r'\d+', text)
            if len(numbers) >= 3:
                for i in range(len(numbers) - 2):
                    sys_val = int(numbers[i])
                    dia_val = int(numbers[i+1])
                    pr_val = int(numbers[i+2])
                    
                    if 60 <= sys_val <= 300 and 30 <= dia_val <= 200 and 30 <= pr_val <= 200:
                        if sys_val > dia_val:
                            return BloodPressureReading(
                                systolic=sys_val,
                                diastolic=dia_val,
                                pulse=pr_val,
                                timestamp=datetime.now()
                            )
        except Exception:
            pass
        return None
    
    @staticmethod
    def _parse_format_bytes(data: bytes) -> Optional[BloodPressureReading]:
        """解析二进制格式"""
        try:
            if len(data) >= 6:
                for offset in range(len(data) - 2):
                    sys_val = data[offset]
                    dia_val = data[offset + 1]
                    pr_val = data[offset + 2]
                    
                    if 60 <= sys_val <= 250 and 30 <= dia_val <= 150 and 30 <= pr_val <= 180:
                        if sys_val > dia_val:
                            return BloodPressureReading(
                                systolic=sys_val,
                                diastolic=dia_val,
                                pulse=pr_val,
                                timestamp=datetime.now()
                            )
        except Exception:
            pass
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
        
        while self.is_running and self.serial_port and self.serial_port.is_open:
            try:
                if self.serial_port.in_waiting > 0:
                    data = self.serial_port.read(self.serial_port.in_waiting)
                    buffer += data
                    
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
        self.root.title("OMRON HBP-9030 血压监测")
        self.root.geometry("700x750")
        self.root.configure(bg=self.COLORS['bg_dark'])
        self.root.resizable(True, True)
        self.root.minsize(600, 650)
        
        # 设置窗口图标（如果有的话）
        try:
            # 尝试设置图标
            pass
        except Exception:
            pass
        
        # 数据
        self.readings: List[BloodPressureReading] = []
        self.data_queue = queue.Queue()
        self.simulation_mode = False
        
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
        main_frame = tk.Frame(self.root, bg=self.COLORS['bg_dark'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 标题
        title_label = tk.Label(
            main_frame,
            text="OMRON HBP-9030 血压监测",
            font=('Microsoft YaHei UI', 24, 'bold'),
            fg=self.COLORS['text_primary'],
            bg=self.COLORS['bg_dark']
        )
        title_label.pack(pady=(0, 20))
        
        # 连接控制区
        self._create_connection_frame(main_frame)
        
        # 血压显示区
        self._create_display_frame(main_frame)
        
        # 历史记录区
        self._create_history_frame(main_frame)
        
        # 日志区
        self._create_log_frame(main_frame)
    
    def _create_connection_frame(self, parent):
        """创建连接控制区"""
        frame = tk.Frame(parent, bg=self.COLORS['bg_medium'], padx=15, pady=15)
        frame.pack(fill=tk.X, pady=(0, 15))
        
        # 第一行：端口和波特率选择
        port_frame = tk.Frame(frame, bg=self.COLORS['bg_medium'])
        port_frame.pack(fill=tk.X)
        
        tk.Label(
            port_frame,
            text="串口:",
            font=('Microsoft YaHei UI', 11),
            fg=self.COLORS['text_primary'],
            bg=self.COLORS['bg_medium']
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(
            port_frame,
            textvariable=self.port_var,
            state='readonly',
            width=15,
            font=('Consolas', 10)
        )
        self.port_combo.pack(side=tk.LEFT, padx=(0, 10))
        
        refresh_btn = tk.Button(
            port_frame,
            text="刷新",
            font=('Microsoft YaHei UI', 10),
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
            font=('Microsoft YaHei UI', 11),
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
            font=('Consolas', 10)
        )
        baudrate_combo.pack(side=tk.LEFT, padx=(0, 20))
        
        # 连接按钮
        self.connect_btn = tk.Button(
            port_frame,
            text="连接",
            font=('Microsoft YaHei UI', 11, 'bold'),
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
            font=('Microsoft YaHei UI', 10),
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
            font=('Microsoft YaHei UI', 10),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        self.sim_interval_var = tk.StringVar(value='5')
        sim_interval_entry = tk.Entry(
            mode_frame,
            textvariable=self.sim_interval_var,
            width=5,
            font=('Consolas', 10),
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
            font=('Microsoft YaHei UI', 10),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        )
        self.status_label.pack(side=tk.LEFT, padx=(8, 0))
    
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
            font=('Microsoft YaHei UI', 14),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        ).pack()
        
        self.sys_value = tk.Label(
            sys_frame,
            text="---",
            font=('Segoe UI', 56, 'bold'),
            fg=self.COLORS['accent'],
            bg=self.COLORS['bg_medium']
        )
        self.sys_value.pack()
        
        tk.Label(
            sys_frame,
            text="mmHg",
            font=('Microsoft YaHei UI', 12),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        ).pack()
        
        # 舒张压
        dia_frame = tk.Frame(display_container, bg=self.COLORS['bg_medium'])
        dia_frame.grid(row=0, column=1, sticky='nsew', padx=10)
        
        tk.Label(
            dia_frame,
            text="舒张压",
            font=('Microsoft YaHei UI', 14),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        ).pack()
        
        self.dia_value = tk.Label(
            dia_frame,
            text="---",
            font=('Segoe UI', 56, 'bold'),
            fg=self.COLORS['accent_light'],
            bg=self.COLORS['bg_medium']
        )
        self.dia_value.pack()
        
        tk.Label(
            dia_frame,
            text="mmHg",
            font=('Microsoft YaHei UI', 12),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        ).pack()
        
        # 心率
        pr_frame = tk.Frame(display_container, bg=self.COLORS['bg_medium'])
        pr_frame.grid(row=0, column=2, sticky='nsew', padx=10)
        
        tk.Label(
            pr_frame,
            text="心率",
            font=('Microsoft YaHei UI', 14),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        ).pack()
        
        self.pr_value = tk.Label(
            pr_frame,
            text="---",
            font=('Segoe UI', 56, 'bold'),
            fg=self.COLORS['success'],
            bg=self.COLORS['bg_medium']
        )
        self.pr_value.pack()
        
        tk.Label(
            pr_frame,
            text="bpm",
            font=('Microsoft YaHei UI', 12),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        ).pack()
        
        self.update_time_label = tk.Label(
            frame,
            text="等待测量数据...",
            font=('Microsoft YaHei UI', 10),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        )
        self.update_time_label.pack(pady=(15, 0))
    
    def _create_history_frame(self, parent):
        """创建历史记录区"""
        frame = tk.Frame(parent, bg=self.COLORS['bg_medium'], padx=15, pady=15)
        frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        header_frame = tk.Frame(frame, bg=self.COLORS['bg_medium'])
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(
            header_frame,
            text="历史记录",
            font=('Microsoft YaHei UI', 12, 'bold'),
            fg=self.COLORS['text_primary'],
            bg=self.COLORS['bg_medium']
        ).pack(side=tk.LEFT)
        
        clear_btn = tk.Button(
            header_frame,
            text="清空",
            font=('Microsoft YaHei UI', 9),
            bg=self.COLORS['bg_light'],
            fg=self.COLORS['text_secondary'],
            activebackground=self.COLORS['danger'],
            activeforeground=self.COLORS['text_primary'],
            relief=tk.FLAT,
            cursor='hand2',
            command=self._clear_history
        )
        clear_btn.pack(side=tk.RIGHT)
        
        list_frame = tk.Frame(frame, bg=self.COLORS['bg_dark'])
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.history_listbox = tk.Listbox(
            list_frame,
            font=('Consolas', 11),
            bg=self.COLORS['bg_dark'],
            fg=self.COLORS['text_primary'],
            selectbackground=self.COLORS['accent'],
            selectforeground=self.COLORS['text_primary'],
            highlightthickness=0,
            relief=tk.FLAT,
            yscrollcommand=scrollbar.set
        )
        self.history_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.history_listbox.yview)
    
    def _create_log_frame(self, parent):
        """创建日志区"""
        self.log_expanded = tk.BooleanVar(value=False)
        
        toggle_frame = tk.Frame(parent, bg=self.COLORS['bg_dark'])
        toggle_frame.pack(fill=tk.X)
        
        self.toggle_log_btn = tk.Button(
            toggle_frame,
            text="▶ 显示原始数据日志（调试用）",
            font=('Microsoft YaHei UI', 9),
            bg=self.COLORS['bg_dark'],
            fg=self.COLORS['text_secondary'],
            activebackground=self.COLORS['bg_dark'],
            activeforeground=self.COLORS['text_primary'],
            relief=tk.FLAT,
            cursor='hand2',
            command=self._toggle_log
        )
        self.toggle_log_btn.pack(anchor='w')
        
        self.log_frame = tk.Frame(parent, bg=self.COLORS['bg_dark'])
        
        log_scrollbar = tk.Scrollbar(self.log_frame)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.log_text = tk.Text(
            self.log_frame,
            font=('Consolas', 9),
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
            self.toggle_log_btn.config(text="▶ 显示原始数据日志（调试用）")
            self.log_expanded.set(False)
        else:
            self.log_frame.pack(fill=tk.X, pady=(5, 0))
            self.toggle_log_btn.config(text="▼ 隐藏原始数据日志")
            self.log_expanded.set(True)
    
    def _refresh_ports(self):
        """刷新串口列表"""
        ports = SerialConnection.get_port_info()
        port_names = [p[0] for p in ports]
        
        self.port_combo['values'] = port_names
        if port_names:
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
                self.status_indicator.delete('all')
                self.status_indicator.create_oval(2, 2, 10, 10, fill=self.COLORS['simulation'], outline='')
                self.status_label.config(text="模拟模式", fg=self.COLORS['simulation'])
            else:
                self.connect_btn.config(text="断开", bg=self.COLORS['danger'], state='normal')
                self.sim_btn.config(state='disabled')
                self.status_indicator.delete('all')
                self.status_indicator.create_oval(2, 2, 10, 10, fill=self.COLORS['success'], outline='')
                self.status_label.config(text="已连接", fg=self.COLORS['success'])
        else:
            self.connect_btn.config(text="连接", bg=self.COLORS['success'], state='normal')
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
            elif value < 120:
                return self.COLORS['success']
            elif value < 140:
                return self.COLORS['warning']
            else:
                return self.COLORS['danger']
        else:
            if value < 60:
                return self.COLORS['warning']
            elif value < 80:
                return self.COLORS['success']
            elif value < 90:
                return self.COLORS['warning']
            else:
                return self.COLORS['danger']
    
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


def main():
    """主函数"""
    logger.info("启动 OMRON HBP-9030 血压监测程序")
    
    # 检查环境
    if not SERIAL_AVAILABLE:
        logger.warning("pyserial库未安装，将只能使用模拟模式")
    
    app = BloodPressureMonitorGUI()
    app.run()


if __name__ == '__main__':
    main()

```

```bat
@echo off
chcp 65001 >nul
echo ============================================
echo    OMRON HBP-9030 血压监测程序 - 打包工具
echo ============================================
echo.

:: 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python，请先安装Python 3.7+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/4] 检测到Python环境
python --version

:: 安装依赖
echo.
echo [2/4] 安装依赖包...
pip install pyserial pyinstaller -q

if errorlevel 1 (
    echo [错误] 安装依赖失败
    pause
    exit /b 1
)

echo      依赖安装完成

:: 打包
echo.
echo [3/4] 开始打包程序...
echo      这可能需要1-3分钟，请耐心等待...
echo.

pyinstaller --onefile --windowed --name "血压监测程序" --clean --noconfirm bp_monitor.py

if errorlevel 1 (
    echo.
    echo [错误] 打包失败
    pause
    exit /b 1
)

:: 完成
echo.
echo [4/4] 打包完成!
echo.
echo ============================================
echo 生成的文件位置:
echo   dist\血压监测程序.exe
echo.
echo 你可以将这个exe文件复制到任何Windows电脑上运行
echo 无需安装Python或任何依赖
echo ============================================
echo.

:: 打开输出目录
explorer dist

pause

```

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
打包脚本 - 将血压监测程序打包为独立exe
使用方法: python build_exe.py
"""

import subprocess
import sys
import os

def main():
    print("=" * 50)
    print("  OMRON HBP-9030 血压监测程序 - 打包工具")
    print("=" * 50)
    print()
    
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # 检查主程序文件
    if not os.path.exists("bp_monitor.py"):
        print("[错误] 找不到 bp_monitor.py 文件")
        print("请确保此脚本与 bp_monitor.py 在同一目录")
        input("按回车键退出...")
        return 1
    
    # 安装依赖
    print("[1/3] 安装依赖包...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", 
            "pyserial", "pyinstaller", "-q"
        ])
        print("      依赖安装完成")
    except subprocess.CalledProcessError as e:
        print(f"[错误] 安装依赖失败: {e}")
        input("按回车键退出...")
        return 1
    
    # 执行打包
    print()
    print("[2/3] 开始打包程序...")
    print("      这可能需要1-3分钟，请耐心等待...")
    print()
    
    try:
        subprocess.check_call([
            sys.executable, "-m", "PyInstaller",
            "--onefile",           # 打包成单个exe
            "--windowed",          # 不显示控制台窗口
            "--name", "血压监测程序",  # exe名称
            "--clean",             # 清理临时文件
            "--noconfirm",         # 不询问确认
            "bp_monitor.py"
        ])
    except subprocess.CalledProcessError as e:
        print()
        print(f"[错误] 打包失败: {e}")
        input("按回车键退出...")
        return 1
    
    # 完成
    print()
    print("[3/3] 打包完成!")
    print()
    print("=" * 50)
    print("生成的文件位置:")
    print(f"  {os.path.join(script_dir, 'dist', '血压监测程序.exe')}")
    print()
    print("你可以将这个exe文件复制到任何Windows电脑上运行")
    print("无需安装Python或任何依赖")
    print("=" * 50)
    print()
    
    # 尝试打开输出目录
    dist_dir = os.path.join(script_dir, "dist")
    if os.path.exists(dist_dir):
        try:
            os.startfile(dist_dir)
        except Exception:
            pass
    
    input("按回车键退出...")
    return 0

if __name__ == "__main__":
    sys.exit(main())

```

```plaintext
================================================================================
                    OMRON HBP-9030 血压监测程序
                         使用说明
================================================================================

【程序功能】
- 通过USB连接欧姆龙HBP-9030血压计
- 实时显示测量的血压和心率数据
- 测量完成后自动接收并显示结果
- 保存历史测量记录

================================================================================

【方式一】直接运行exe文件（推荐，无需安装任何软件）
--------------------------------------------------------------------------------
1. 将「血压监测程序.exe」复制到目标电脑
2. 双击运行即可
3. 如果提示"Windows已保护你的电脑"，点击"更多信息"→"仍要运行"

================================================================================

【方式二】打包生成exe文件（需要Python环境）
--------------------------------------------------------------------------------
如果你收到的是源代码而不是exe文件，需要先打包：

1. 安装Python（如果没有安装）
   - 下载地址: https://www.python.org/downloads/
   - 安装时勾选"Add Python to PATH"

2. 打包程序（两种方式任选其一）
   
   方式A：双击运行 build.bat
   
   方式B：在命令行运行
         python build_exe.py

3. 打包完成后，exe文件在 dist 文件夹中

================================================================================

【使用步骤】
--------------------------------------------------------------------------------
1. 用USB线连接HBP-9030血压计到电脑

2. 打开程序

3. 在"串口"下拉菜单中选择对应的COM端口
   - 如果看不到端口，点击"刷新"按钮
   - 如果仍然看不到，请检查USB线是否连接好

4. 点击"连接"按钮

5. 在血压计上进行测量
   - 测量完成后，数据会自动显示在程序界面上

6. 使用完毕后，点击"断开"按钮

================================================================================

【模拟模式】（用于测试，无需真实设备）
--------------------------------------------------------------------------------
如果暂时没有血压计，可以使用模拟模式测试程序功能：

1. 点击"启动模拟模式"按钮
2. 程序会每隔几秒自动生成模拟的血压数据
3. 可以调整"间隔(秒)"来改变数据生成频率
4. 点击"停止模拟模式"结束

================================================================================

【常见问题】
--------------------------------------------------------------------------------

Q: 检测不到串口怎么办？
A: 
   1. 检查USB线是否连接牢固
   2. 打开Windows设备管理器，查看"端口(COM和LPT)"下是否有新设备
   3. 如果显示黄色感叹号，可能需要安装驱动
   4. 尝试换一个USB接口

Q: 连接后收不到数据怎么办？
A: 
   1. 确认血压计已开启USB输出功能（参考血压计说明书）
   2. 尝试更换波特率（常用：9600、19200、115200）
   3. 展开"原始数据日志"查看是否有数据接收
   4. 查看程序目录下的 bp_monitor.log 文件

Q: 数据显示不正确怎么办？
A: 
   1. 展开"原始数据日志"查看原始数据格式
   2. 将日志信息反馈给开发人员进行调整

Q: 程序打不开/闪退怎么办？
A: 
   1. 右键点击exe，选择"以管理员身份运行"
   2. 检查是否被杀毒软件拦截
   3. 查看程序目录下的 bp_monitor.log 文件

================================================================================

【血压值颜色说明】
--------------------------------------------------------------------------------
绿色：正常范围
黄色：偏低或偏高（正常高值）
红色：高血压

收缩压(高压)参考范围：
  - 正常：90-119 mmHg
  - 正常高值：120-139 mmHg
  - 高血压：≥140 mmHg

舒张压(低压)参考范围：
  - 正常：60-79 mmHg
  - 正常高值：80-89 mmHg
  - 高血压：≥90 mmHg

================================================================================

【技术支持】
--------------------------------------------------------------------------------
如有问题，请提供以下信息：
1. 程序目录下的 bp_monitor.log 文件
2. Windows版本
3. 血压计型号和设置

================================================================================

```

```plaintext
================================================================================
              远程指导非技术人员安装程序 - 简化步骤
================================================================================

【准备工作】
你需要提前做好以下准备：
1. 在你的电脑上运行 build.bat 生成 exe 文件
2. 将 dist 文件夹中的「血压监测程序.exe」和「使用说明.txt」发给对方
   （可以通过微信、邮件、U盘等方式）

================================================================================

【远程指导步骤】（电话/微信指导对方）
================================================================================

第一步：把文件放到桌面
--------------------------------------------------------------------------------
"我发给你的文件收到了吗？把那个「血压监测程序.exe」复制到桌面上"

--------------------------------------------------------------------------------

第二步：运行程序
--------------------------------------------------------------------------------
"双击那个程序图标"

如果弹出安全提示：
"如果弹出蓝色的窗口说'Windows已保护你的电脑'，
 点击下面那行小字'更多信息'，
 然后点击'仍要运行'按钮"

--------------------------------------------------------------------------------

第三步：连接血压计
--------------------------------------------------------------------------------
"程序打开了吗？好的。
 现在用USB线把血压计连到电脑上"

"连好了吗？点击程序里那个'刷新'按钮"

"串口那里有没有出现COM什么的选项？
 - 如果有：选择那个，然后点'连接'
 - 如果没有：等我看看..." 
 
（如果没有，参考下面的"故障排除"）

--------------------------------------------------------------------------------

第四步：测试
--------------------------------------------------------------------------------
"连接成功了吗？状态那里显示绿色的'已连接'吗？
 好，现在你用血压计测量一下血压，
 测完之后看看程序上有没有显示数字"

--------------------------------------------------------------------------------

第五步：确认完成
--------------------------------------------------------------------------------
"显示血压数值了吗？太好了，说明一切正常！
 以后每次用的时候：
 1. 先打开程序
 2. 连接血压计
 3. 点连接
 4. 然后正常测量就行"

================================================================================

【故障排除】
================================================================================

问题1：检测不到串口
--------------------------------------------------------------------------------
"你打开'此电脑'，右键点击，选择'管理'，
 左边找到'设备管理器'点一下，
 右边找找有没有'端口(COM和LPT)'这一项，
 点开它，看看里面有没有东西"

- 如果有设备但带黄色感叹号："需要安装驱动，我帮你查一下"
- 如果完全没有："换一个USB接口试试"
- 如果还是没有："可能USB线有问题，或者血压计需要开启什么设置"

--------------------------------------------------------------------------------

问题2：程序打不开
--------------------------------------------------------------------------------
"右键点击程序图标，选择'以管理员身份运行'试试"

如果还是不行：
"你用的Windows是什么版本？Win7还是Win10还是Win11？"
（Win7可能需要安装额外的运行库）

--------------------------------------------------------------------------------

问题3：连接上了但收不到数据
--------------------------------------------------------------------------------
"点一下程序下面那个'显示原始数据日志'，
 然后测量一下血压，看看日志里有没有东西出现"

- 如果有东西出现但数据不对："把日志截图发给我看看"
- 如果什么都没有："试试换一个波特率，比如改成19200再连接试试"

================================================================================

【应急方案】使用模拟模式
================================================================================
如果实在连接不上，可以先用模拟模式让对方熟悉程序：

"你先点那个紫色的'启动模拟模式'按钮，
 这样程序会自动显示一些测试数据，
 你可以先熟悉一下界面，
 等我查清楚连接问题再帮你连接真正的血压计"

================================================================================

```

```pip-requirements
# OMRON HBP-9030 血压监测程序依赖
# Python 3.7+ required

# 串口通信
pyserial>=3.5

# 打包工具（仅打包时需要）
# pyinstaller>=5.0


```

所有任务已完成！我来总结一下优化后的方案：

## 优化总结

### 1. 程序改进

**添加了模拟模式**
- 无需真实设备即可测试程序
- 可调节数据生成间隔
- 生成合理范围内的随机血压数据

**改进了错误处理**
- 更友好的错误提示信息
- 自动处理 pyserial 未安装的情况
- 更好的串口错误处理（端口占用、设备不存在等）

### 2. 创建的文件

| 文件 | 用途 |
|------|------|
| `bp_monitor.py` | 主程序（已优化） |
| `build.bat` | 一键打包脚本（双击运行） |
| `build_exe.py` | Python打包脚本（备用） |
| `使用说明.txt` | 终端用户使用指南 |
| `远程指导步骤.txt` | 远程指导话术（给你用的） |
| `requirements.txt` | 依赖清单 |

### 3. 如何让医院使用

**最简单的部署方式**：

1. **你先打包**：在你的电脑上双击 `build.bat`，等待生成 exe 文件

2. **发送给医院**：把 `dist\血压监测程序.exe` 和 `使用说明.txt` 发给对方

3. **对方使用**：双击 exe 即可运行，无需安装任何东西

### 4. 远程指导要点

- `远程指导步骤.txt` 包含了详细的电话指导话术
- 步骤已经简化到非技术人员也能理解
- 包含常见问题的排查方法

### 5. 建议的测试流程

1. **先在你的电脑上测试**：运行程序，使用"模拟模式"验证界面正常
2. **打包**：双击 `build.bat`
3. **测试打包结果**：运行 `dist\血压监测程序.exe` 确认正常
4. **发送给医院**：连同使用说明一起发送
5. **远程指导安装**：用 `远程指导步骤.txt` 中的话术指导对方

---

**User**

现在默认串口接收到的数据模式是怎么样的，进行了什么数据处理？如果实际接收的数据结构不一样，应该修改哪块代码？模拟模式是模拟串口接收到的数据，然后读取、显示，还是随机出数据直接显示了？

---

**Cursor**

让我再看一下模拟器和串口读取的完整逻辑：

很好的问题！让我详细解释一下：

## 1. 当前支持的数据格式

`DataParser` 类（第80-248行）会**依次尝试5种格式**解析：

| 方法 | 格式示例 | 说明 |
|------|----------|------|
| `_parse_format_csv` | `120,80,72` 或 `2026,1,20,14,30,120,80,72` | 逗号分隔，找3个连续的合理数字 |
| `_parse_format_space` | `120 80 72` | 空格/制表符分隔 |
| `_parse_format_labeled` | `SYS:120 DIA:80 PR:72` 或 `120/80 72` | 带标签或斜杠格式 |
| `_parse_format_numeric` | `DATA20260120120807265` | 从任意文本提取数字 |
| `_parse_format_bytes` | `0x78 0x50 0x48` (二进制) | 连续3字节作为SYS/DIA/PR |

**数据验证条件**：
- 收缩压(SYS)：60-300 mmHg
- 舒张压(DIA)：30-200 mmHg  
- 心率(PR)：30-200 bpm
- 且 SYS > DIA

## 2. 数据处理流程

```
串口接收字节 → 按换行符(\r\n)分割 → DataParser.parse() → 尝试5种格式 → 显示
```

关键代码在 `SerialConnection._read_loop()`（第419-457行）：

```131:150:C:\Users\zhangxc\Desktop\py_work\OMRON\bp_monitor.py
    @staticmethod
    def _parse_format_csv(text: str) -> Optional[BloodPressureReading]:
        """解析CSV格式: 日期,时间,SYS,DIA,PR 或类似格式"""
        try:
            parts = text.split(',')
            if len(parts) >= 3:
                numbers = []
                for p in parts:
                    p = p.strip()
                    if p.isdigit():
                        numbers.append(int(p))
                
                for i in range(len(numbers) - 2):
                    sys_val, dia_val, pr_val = numbers[i], numbers[i+1], numbers[i+2]
                    if 60 <= sys_val <= 300 and 30 <= dia_val <= 200 and 30 <= pr_val <= 200:
                        if sys_val > dia_val:
                            return BloodPressureReading(
                                systolic=sys_val,
                                diastolic=dia_val,
                                pulse=pr_val,
                                timestamp=datetime.now()
                            )
```

## 3. 模拟模式的问题

你说得对！**当前模拟模式是直接生成数据显示，跳过了解析流程**：

```296:311:C:\Users\zhangxc\Desktop\py_work\OMRON\bp_monitor.py
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
```

## 4. 如果实际格式不同，应该修改哪里

**主要修改 `DataParser` 类**。我来演示如何添加一个新的解析格式。

假设真实设备发送的格式是：`STX,ID,YYYY,MM,DD,HH,MM,SYS,DIA,PR,ETX`，例如：
```
STX,001,2026,01,20,14,30,125,82,68,ETX
```

你可以这样添加新的解析方法：

```plaintext
串口接收字节 → 按换行符(\r\n)分割 → DataParser.parse() → 尝试5种格式 → 显示
```

```plaintext
    @staticmethod
    def _parse_format_csv(text: str) -> Optional[BloodPressureReading]:
        """解析CSV格式: 日期,时间,SYS,DIA,PR 或类似格式"""
        try:
            parts = text.split(',')
            if len(parts) >= 3:
                numbers = []
                for p in parts:
                    p = p.strip()
                    if p.isdigit():
                        numbers.append(int(p))
                
                for i in range(len(numbers) - 2):
                    sys_val, dia_val, pr_val = numbers[i], numbers[i+1], numbers[i+2]
                    if 60 <= sys_val <= 300 and 30 <= dia_val <= 200 and 30 <= pr_val <= 200:
                        if sys_val > dia_val:
                            return BloodPressureReading(
                                systolic=sys_val,
                                diastolic=dia_val,
                                pulse=pr_val,
                                timestamp=datetime.now()
                            )
```

```plaintext
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
```

```plaintext
STX,001,2026,01,20,14,30,125,82,68,ETX
```

```python
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
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import re
import random
import time
import os
import sys
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
    支持多种可能的数据格式
    """
    
    @staticmethod
    def parse(data: bytes) -> Optional[BloodPressureReading]:
        """
        尝试解析血压数据
        支持多种格式的自动识别
        """
        try:
            # 尝试不同的编码方式解码
            text = ""
            for encoding in ['ascii', 'utf-8', 'latin-1', 'gbk']:
                try:
                    text = data.decode(encoding).strip()
                    break
                except (UnicodeDecodeError, LookupError):
                    continue
            
            if not text:
                text = data.decode('ascii', errors='ignore').strip()
            
            if not text:
                return None
                
            logger.debug(f"接收原始数据: {repr(text)}")
            logger.debug(f"十六进制: {data.hex()}")
            
            # 尝试多种格式解析（按优先级顺序）
            # 如果你知道设备的确切格式，可以把对应的解析方法放在最前面
            result = (
                DataParser._parse_format_hbp9030(text) or  # HBP-9030专用格式（优先）
                DataParser._parse_format_csv(text) or
                DataParser._parse_format_space(text) or
                DataParser._parse_format_labeled(text) or
                DataParser._parse_format_numeric(text) or
                DataParser._parse_format_bytes(data)
            )
            
            if result:
                result.raw_data = text
                logger.info(f"解析成功: SYS={result.systolic}, DIA={result.diastolic}, PR={result.pulse}")
            
            return result
            
        except Exception as e:
            logger.error(f"解析数据时出错: {e}")
            return None
    
    @staticmethod
    def _parse_format_csv(text: str) -> Optional[BloodPressureReading]:
        """解析CSV格式: 日期,时间,SYS,DIA,PR 或类似格式"""
        try:
            parts = text.split(',')
            if len(parts) >= 3:
                numbers = []
                for p in parts:
                    p = p.strip()
                    if p.isdigit():
                        numbers.append(int(p))
                
                for i in range(len(numbers) - 2):
                    sys_val, dia_val, pr_val = numbers[i], numbers[i+1], numbers[i+2]
                    if 60 <= sys_val <= 300 and 30 <= dia_val <= 200 and 30 <= pr_val <= 200:
                        if sys_val > dia_val:
                            return BloodPressureReading(
                                systolic=sys_val,
                                diastolic=dia_val,
                                pulse=pr_val,
                                timestamp=datetime.now()
                            )
        except Exception:
            pass
        return None
    
    @staticmethod
    def _parse_format_space(text: str) -> Optional[BloodPressureReading]:
        """解析空格分隔格式"""
        try:
            parts = text.split()
            numbers = [int(p) for p in parts if p.isdigit()]
            
            for i in range(len(numbers) - 2):
                sys_val, dia_val, pr_val = numbers[i], numbers[i+1], numbers[i+2]
                if 60 <= sys_val <= 300 and 30 <= dia_val <= 200 and 30 <= pr_val <= 200:
                    if sys_val > dia_val:
                        return BloodPressureReading(
                            systolic=sys_val,
                            diastolic=dia_val,
                            pulse=pr_val,
                            timestamp=datetime.now()
                        )
        except Exception:
            pass
        return None
    
    @staticmethod
    def _parse_format_labeled(text: str) -> Optional[BloodPressureReading]:
        """解析带标签格式: SYS:120 DIA:80 PR:72 等"""
        try:
            sys_match = re.search(r'(?:SYS|sys|收缩|高压)[:\s=]*(\d+)', text)
            dia_match = re.search(r'(?:DIA|dia|舒张|低压)[:\s=]*(\d+)', text)
            pr_match = re.search(r'(?:PR|pr|HR|hr|脉搏|心率|PULSE|pulse)[:\s=]*(\d+)', text)
            
            if sys_match and dia_match and pr_match:
                return BloodPressureReading(
                    systolic=int(sys_match.group(1)),
                    diastolic=int(dia_match.group(1)),
                    pulse=int(pr_match.group(1)),
                    timestamp=datetime.now()
                )
            
            bp_match = re.search(r'(\d{2,3})\s*/\s*(\d{2,3})\s+(\d{2,3})', text)
            if bp_match:
                return BloodPressureReading(
                    systolic=int(bp_match.group(1)),
                    diastolic=int(bp_match.group(2)),
                    pulse=int(bp_match.group(3)),
                    timestamp=datetime.now()
                )
        except Exception:
            pass
        return None
    
    @staticmethod
    def _parse_format_numeric(text: str) -> Optional[BloodPressureReading]:
        """解析纯数字格式"""
        try:
            numbers = re.findall(r'\d+', text)
            if len(numbers) >= 3:
                for i in range(len(numbers) - 2):
                    sys_val = int(numbers[i])
                    dia_val = int(numbers[i+1])
                    pr_val = int(numbers[i+2])
                    
                    if 60 <= sys_val <= 300 and 30 <= dia_val <= 200 and 30 <= pr_val <= 200:
                        if sys_val > dia_val:
                            return BloodPressureReading(
                                systolic=sys_val,
                                diastolic=dia_val,
                                pulse=pr_val,
                                timestamp=datetime.now()
                            )
        except Exception:
            pass
        return None
    
    @staticmethod
    def _parse_format_bytes(data: bytes) -> Optional[BloodPressureReading]:
        """解析二进制格式"""
        try:
            if len(data) >= 6:
                for offset in range(len(data) - 2):
                    sys_val = data[offset]
                    dia_val = data[offset + 1]
                    pr_val = data[offset + 2]
                    
                    if 60 <= sys_val <= 250 and 30 <= dia_val <= 150 and 30 <= pr_val <= 180:
                        if sys_val > dia_val:
                            return BloodPressureReading(
                                systolic=sys_val,
                                diastolic=dia_val,
                                pulse=pr_val,
                                timestamp=datetime.now()
                            )
        except Exception:
            pass
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
        
        while self.is_running and self.serial_port and self.serial_port.is_open:
            try:
                if self.serial_port.in_waiting > 0:
                    data = self.serial_port.read(self.serial_port.in_waiting)
                    buffer += data
                    
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
        self.root.title("OMRON HBP-9030 血压监测")
        self.root.geometry("700x750")
        self.root.configure(bg=self.COLORS['bg_dark'])
        self.root.resizable(True, True)
        self.root.minsize(600, 650)
        
        # 设置窗口图标（如果有的话）
        try:
            # 尝试设置图标
            pass
        except Exception:
            pass
        
        # 数据
        self.readings: List[BloodPressureReading] = []
        self.data_queue = queue.Queue()
        self.simulation_mode = False
        
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
        main_frame = tk.Frame(self.root, bg=self.COLORS['bg_dark'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 标题
        title_label = tk.Label(
            main_frame,
            text="OMRON HBP-9030 血压监测",
            font=('Microsoft YaHei UI', 24, 'bold'),
            fg=self.COLORS['text_primary'],
            bg=self.COLORS['bg_dark']
        )
        title_label.pack(pady=(0, 20))
        
        # 连接控制区
        self._create_connection_frame(main_frame)
        
        # 血压显示区
        self._create_display_frame(main_frame)
        
        # 历史记录区
        self._create_history_frame(main_frame)
        
        # 日志区
        self._create_log_frame(main_frame)
    
    def _create_connection_frame(self, parent):
        """创建连接控制区"""
        frame = tk.Frame(parent, bg=self.COLORS['bg_medium'], padx=15, pady=15)
        frame.pack(fill=tk.X, pady=(0, 15))
        
        # 第一行：端口和波特率选择
        port_frame = tk.Frame(frame, bg=self.COLORS['bg_medium'])
        port_frame.pack(fill=tk.X)
        
        tk.Label(
            port_frame,
            text="串口:",
            font=('Microsoft YaHei UI', 11),
            fg=self.COLORS['text_primary'],
            bg=self.COLORS['bg_medium']
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(
            port_frame,
            textvariable=self.port_var,
            state='readonly',
            width=15,
            font=('Consolas', 10)
        )
        self.port_combo.pack(side=tk.LEFT, padx=(0, 10))
        
        refresh_btn = tk.Button(
            port_frame,
            text="刷新",
            font=('Microsoft YaHei UI', 10),
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
            font=('Microsoft YaHei UI', 11),
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
            font=('Consolas', 10)
        )
        baudrate_combo.pack(side=tk.LEFT, padx=(0, 20))
        
        # 连接按钮
        self.connect_btn = tk.Button(
            port_frame,
            text="连接",
            font=('Microsoft YaHei UI', 11, 'bold'),
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
            font=('Microsoft YaHei UI', 10),
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
            font=('Microsoft YaHei UI', 10),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        self.sim_interval_var = tk.StringVar(value='5')
        sim_interval_entry = tk.Entry(
            mode_frame,
            textvariable=self.sim_interval_var,
            width=5,
            font=('Consolas', 10),
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
            font=('Microsoft YaHei UI', 10),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        )
        self.status_label.pack(side=tk.LEFT, padx=(8, 0))
    
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
            font=('Microsoft YaHei UI', 14),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        ).pack()
        
        self.sys_value = tk.Label(
            sys_frame,
            text="---",
            font=('Segoe UI', 56, 'bold'),
            fg=self.COLORS['accent'],
            bg=self.COLORS['bg_medium']
        )
        self.sys_value.pack()
        
        tk.Label(
            sys_frame,
            text="mmHg",
            font=('Microsoft YaHei UI', 12),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        ).pack()
        
        # 舒张压
        dia_frame = tk.Frame(display_container, bg=self.COLORS['bg_medium'])
        dia_frame.grid(row=0, column=1, sticky='nsew', padx=10)
        
        tk.Label(
            dia_frame,
            text="舒张压",
            font=('Microsoft YaHei UI', 14),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        ).pack()
        
        self.dia_value = tk.Label(
            dia_frame,
            text="---",
            font=('Segoe UI', 56, 'bold'),
            fg=self.COLORS['accent_light'],
            bg=self.COLORS['bg_medium']
        )
        self.dia_value.pack()
        
        tk.Label(
            dia_frame,
            text="mmHg",
            font=('Microsoft YaHei UI', 12),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        ).pack()
        
        # 心率
        pr_frame = tk.Frame(display_container, bg=self.COLORS['bg_medium'])
        pr_frame.grid(row=0, column=2, sticky='nsew', padx=10)
        
        tk.Label(
            pr_frame,
            text="心率",
            font=('Microsoft YaHei UI', 14),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        ).pack()
        
        self.pr_value = tk.Label(
            pr_frame,
            text="---",
            font=('Segoe UI', 56, 'bold'),
            fg=self.COLORS['success'],
            bg=self.COLORS['bg_medium']
        )
        self.pr_value.pack()
        
        tk.Label(
            pr_frame,
            text="bpm",
            font=('Microsoft YaHei UI', 12),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        ).pack()
        
        self.update_time_label = tk.Label(
            frame,
            text="等待测量数据...",
            font=('Microsoft YaHei UI', 10),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        )
        self.update_time_label.pack(pady=(15, 0))
    
    def _create_history_frame(self, parent):
        """创建历史记录区"""
        frame = tk.Frame(parent, bg=self.COLORS['bg_medium'], padx=15, pady=15)
        frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        header_frame = tk.Frame(frame, bg=self.COLORS['bg_medium'])
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(
            header_frame,
            text="历史记录",
            font=('Microsoft YaHei UI', 12, 'bold'),
            fg=self.COLORS['text_primary'],
            bg=self.COLORS['bg_medium']
        ).pack(side=tk.LEFT)
        
        clear_btn = tk.Button(
            header_frame,
            text="清空",
            font=('Microsoft YaHei UI', 9),
            bg=self.COLORS['bg_light'],
            fg=self.COLORS['text_secondary'],
            activebackground=self.COLORS['danger'],
            activeforeground=self.COLORS['text_primary'],
            relief=tk.FLAT,
            cursor='hand2',
            command=self._clear_history
        )
        clear_btn.pack(side=tk.RIGHT)
        
        list_frame = tk.Frame(frame, bg=self.COLORS['bg_dark'])
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.history_listbox = tk.Listbox(
            list_frame,
            font=('Consolas', 11),
            bg=self.COLORS['bg_dark'],
            fg=self.COLORS['text_primary'],
            selectbackground=self.COLORS['accent'],
            selectforeground=self.COLORS['text_primary'],
            highlightthickness=0,
            relief=tk.FLAT,
            yscrollcommand=scrollbar.set
        )
        self.history_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.history_listbox.yview)
    
    def _create_log_frame(self, parent):
        """创建日志区"""
        self.log_expanded = tk.BooleanVar(value=False)
        
        toggle_frame = tk.Frame(parent, bg=self.COLORS['bg_dark'])
        toggle_frame.pack(fill=tk.X)
        
        self.toggle_log_btn = tk.Button(
            toggle_frame,
            text="▶ 显示原始数据日志（调试用）",
            font=('Microsoft YaHei UI', 9),
            bg=self.COLORS['bg_dark'],
            fg=self.COLORS['text_secondary'],
            activebackground=self.COLORS['bg_dark'],
            activeforeground=self.COLORS['text_primary'],
            relief=tk.FLAT,
            cursor='hand2',
            command=self._toggle_log
        )
        self.toggle_log_btn.pack(anchor='w')
        
        self.log_frame = tk.Frame(parent, bg=self.COLORS['bg_dark'])
        
        log_scrollbar = tk.Scrollbar(self.log_frame)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.log_text = tk.Text(
            self.log_frame,
            font=('Consolas', 9),
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
            self.toggle_log_btn.config(text="▶ 显示原始数据日志（调试用）")
            self.log_expanded.set(False)
        else:
            self.log_frame.pack(fill=tk.X, pady=(5, 0))
            self.toggle_log_btn.config(text="▼ 隐藏原始数据日志")
            self.log_expanded.set(True)
    
    def _refresh_ports(self):
        """刷新串口列表"""
        ports = SerialConnection.get_port_info()
        port_names = [p[0] for p in ports]
        
        self.port_combo['values'] = port_names
        if port_names:
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
                self.status_indicator.delete('all')
                self.status_indicator.create_oval(2, 2, 10, 10, fill=self.COLORS['simulation'], outline='')
                self.status_label.config(text="模拟模式", fg=self.COLORS['simulation'])
            else:
                self.connect_btn.config(text="断开", bg=self.COLORS['danger'], state='normal')
                self.sim_btn.config(state='disabled')
                self.status_indicator.delete('all')
                self.status_indicator.create_oval(2, 2, 10, 10, fill=self.COLORS['success'], outline='')
                self.status_label.config(text="已连接", fg=self.COLORS['success'])
        else:
            self.connect_btn.config(text="连接", bg=self.COLORS['success'], state='normal')
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
            elif value < 120:
                return self.COLORS['success']
            elif value < 140:
                return self.COLORS['warning']
            else:
                return self.COLORS['danger']
        else:
            if value < 60:
                return self.COLORS['warning']
            elif value < 80:
                return self.COLORS['success']
            elif value < 90:
                return self.COLORS['warning']
            else:
                return self.COLORS['danger']
    
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


def main():
    """主函数"""
    logger.info("启动 OMRON HBP-9030 血压监测程序")
    
    # 检查环境
    if not SERIAL_AVAILABLE:
        logger.warning("pyserial库未安装，将只能使用模拟模式")
    
    app = BloodPressureMonitorGUI()
    app.run()


if __name__ == '__main__':
    main()

```

```python
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
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import re
import random
import time
import os
import sys
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
    支持多种可能的数据格式
    """
    
    @staticmethod
    def parse(data: bytes) -> Optional[BloodPressureReading]:
        """
        尝试解析血压数据
        支持多种格式的自动识别
        """
        try:
            # 尝试不同的编码方式解码
            text = ""
            for encoding in ['ascii', 'utf-8', 'latin-1', 'gbk']:
                try:
                    text = data.decode(encoding).strip()
                    break
                except (UnicodeDecodeError, LookupError):
                    continue
            
            if not text:
                text = data.decode('ascii', errors='ignore').strip()
            
            if not text:
                return None
                
            logger.debug(f"接收原始数据: {repr(text)}")
            logger.debug(f"十六进制: {data.hex()}")
            
            # 尝试多种格式解析（按优先级顺序）
            # 如果你知道设备的确切格式，可以把对应的解析方法放在最前面
            result = (
                DataParser._parse_format_hbp9030(text) or  # HBP-9030专用格式（优先）
                DataParser._parse_format_csv(text) or
                DataParser._parse_format_space(text) or
                DataParser._parse_format_labeled(text) or
                DataParser._parse_format_numeric(text) or
                DataParser._parse_format_bytes(data)
            )
            
            if result:
                result.raw_data = text
                logger.info(f"解析成功: SYS={result.systolic}, DIA={result.diastolic}, PR={result.pulse}")
            
            return result
            
        except Exception as e:
            logger.error(f"解析数据时出错: {e}")
            return None
    
    @staticmethod
    def _parse_format_hbp9030(text: str) -> Optional[BloodPressureReading]:
        """
        HBP-9030 专用格式解析
        
        ============================================================
        【重要】请根据实际接收到的数据格式修改此方法！
        ============================================================
        
        当你连接真实设备后，展开"原始数据日志"查看实际格式，
        然后修改下面的解析逻辑。
        
        常见格式示例：
        1. STX,ID,YYYY,MM,DD,HH,MM,SYS,DIA,PR,ETX
           例: STX,001,2026,01,20,14,30,125,82,68,ETX
           
        2. 固定长度格式（每个字段固定宽度）
           例: 001202601201430125082068
           
        3. 带校验和的格式
           例: $BP,125,82,68*5A
        
        当前实现：尝试匹配 STX...ETX 格式，你可以根据实际情况修改
        """
        try:
            # === 格式1: STX,ID,YYYY,MM,DD,HH,MM,SYS,DIA,PR,ETX ===
            if 'STX' in text and 'ETX' in text:
                # 提取STX和ETX之间的内容
                start = text.find('STX')
                end = text.find('ETX')
                if start >= 0 and end > start:
                    content = text[start+3:end].strip(',')
                    parts = content.split(',')
                    # 假设最后3个数字是 SYS, DIA, PR
                    if len(parts) >= 3:
                        try:
                            sys_val = int(parts[-3])
                            dia_val = int(parts[-2])
                            pr_val = int(parts[-1])
                            if 60 <= sys_val <= 300 and 30 <= dia_val <= 200 and 30 <= pr_val <= 200:
                                if sys_val > dia_val:
                                    return BloodPressureReading(
                                        systolic=sys_val,
                                        diastolic=dia_val,
                                        pulse=pr_val,
                                        timestamp=datetime.now()
                                    )
                        except ValueError:
                            pass
            
            # === 格式2: 在这里添加其他格式的解析 ===
            # 例如固定长度格式:
            # if len(text) == 24:  # 固定24字符
            #     sys_val = int(text[15:18])
            #     dia_val = int(text[18:21])
            #     pr_val = int(text[21:24])
            #     ...
            
            # === 格式3: 带校验和格式 ===
            # if text.startswith('$BP,'):
            #     ...
            
        except Exception as e:
            logger.debug(f"HBP-9030格式解析失败: {e}")
        return None
    
    @staticmethod
    def _parse_format_csv(text: str) -> Optional[BloodPressureReading]:
        """解析CSV格式: 日期,时间,SYS,DIA,PR 或类似格式"""
        try:
            parts = text.split(',')
            if len(parts) >= 3:
                numbers = []
                for p in parts:
                    p = p.strip()
                    if p.isdigit():
                        numbers.append(int(p))
                
                for i in range(len(numbers) - 2):
                    sys_val, dia_val, pr_val = numbers[i], numbers[i+1], numbers[i+2]
                    if 60 <= sys_val <= 300 and 30 <= dia_val <= 200 and 30 <= pr_val <= 200:
                        if sys_val > dia_val:
                            return BloodPressureReading(
                                systolic=sys_val,
                                diastolic=dia_val,
                                pulse=pr_val,
                                timestamp=datetime.now()
                            )
        except Exception:
            pass
        return None
    
    @staticmethod
    def _parse_format_space(text: str) -> Optional[BloodPressureReading]:
        """解析空格分隔格式"""
        try:
            parts = text.split()
            numbers = [int(p) for p in parts if p.isdigit()]
            
            for i in range(len(numbers) - 2):
                sys_val, dia_val, pr_val = numbers[i], numbers[i+1], numbers[i+2]
                if 60 <= sys_val <= 300 and 30 <= dia_val <= 200 and 30 <= pr_val <= 200:
                    if sys_val > dia_val:
                        return BloodPressureReading(
                            systolic=sys_val,
                            diastolic=dia_val,
                            pulse=pr_val,
                            timestamp=datetime.now()
                        )
        except Exception:
            pass
        return None
    
    @staticmethod
    def _parse_format_labeled(text: str) -> Optional[BloodPressureReading]:
        """解析带标签格式: SYS:120 DIA:80 PR:72 等"""
        try:
            sys_match = re.search(r'(?:SYS|sys|收缩|高压)[:\s=]*(\d+)', text)
            dia_match = re.search(r'(?:DIA|dia|舒张|低压)[:\s=]*(\d+)', text)
            pr_match = re.search(r'(?:PR|pr|HR|hr|脉搏|心率|PULSE|pulse)[:\s=]*(\d+)', text)
            
            if sys_match and dia_match and pr_match:
                return BloodPressureReading(
                    systolic=int(sys_match.group(1)),
                    diastolic=int(dia_match.group(1)),
                    pulse=int(pr_match.group(1)),
                    timestamp=datetime.now()
                )
            
            bp_match = re.search(r'(\d{2,3})\s*/\s*(\d{2,3})\s+(\d{2,3})', text)
            if bp_match:
                return BloodPressureReading(
                    systolic=int(bp_match.group(1)),
                    diastolic=int(bp_match.group(2)),
                    pulse=int(bp_match.group(3)),
                    timestamp=datetime.now()
                )
        except Exception:
            pass
        return None
    
    @staticmethod
    def _parse_format_numeric(text: str) -> Optional[BloodPressureReading]:
        """解析纯数字格式"""
        try:
            numbers = re.findall(r'\d+', text)
            if len(numbers) >= 3:
                for i in range(len(numbers) - 2):
                    sys_val = int(numbers[i])
                    dia_val = int(numbers[i+1])
                    pr_val = int(numbers[i+2])
                    
                    if 60 <= sys_val <= 300 and 30 <= dia_val <= 200 and 30 <= pr_val <= 200:
                        if sys_val > dia_val:
                            return BloodPressureReading(
                                systolic=sys_val,
                                diastolic=dia_val,
                                pulse=pr_val,
                                timestamp=datetime.now()
                            )
        except Exception:
            pass
        return None
    
    @staticmethod
    def _parse_format_bytes(data: bytes) -> Optional[BloodPressureReading]:
        """解析二进制格式"""
        try:
            if len(data) >= 6:
                for offset in range(len(data) - 2):
                    sys_val = data[offset]
                    dia_val = data[offset + 1]
                    pr_val = data[offset + 2]
                    
                    if 60 <= sys_val <= 250 and 30 <= dia_val <= 150 and 30 <= pr_val <= 180:
                        if sys_val > dia_val:
                            return BloodPressureReading(
                                systolic=sys_val,
                                diastolic=dia_val,
                                pulse=pr_val,
                                timestamp=datetime.now()
                            )
        except Exception:
            pass
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
        
        while self.is_running and self.serial_port and self.serial_port.is_open:
            try:
                if self.serial_port.in_waiting > 0:
                    data = self.serial_port.read(self.serial_port.in_waiting)
                    buffer += data
                    
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
        self.root.title("OMRON HBP-9030 血压监测")
        self.root.geometry("700x750")
        self.root.configure(bg=self.COLORS['bg_dark'])
        self.root.resizable(True, True)
        self.root.minsize(600, 650)
        
        # 设置窗口图标（如果有的话）
        try:
            # 尝试设置图标
            pass
        except Exception:
            pass
        
        # 数据
        self.readings: List[BloodPressureReading] = []
        self.data_queue = queue.Queue()
        self.simulation_mode = False
        
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
        main_frame = tk.Frame(self.root, bg=self.COLORS['bg_dark'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 标题
        title_label = tk.Label(
            main_frame,
            text="OMRON HBP-9030 血压监测",
            font=('Microsoft YaHei UI', 24, 'bold'),
            fg=self.COLORS['text_primary'],
            bg=self.COLORS['bg_dark']
        )
        title_label.pack(pady=(0, 20))
        
        # 连接控制区
        self._create_connection_frame(main_frame)
        
        # 血压显示区
        self._create_display_frame(main_frame)
        
        # 历史记录区
        self._create_history_frame(main_frame)
        
        # 日志区
        self._create_log_frame(main_frame)
    
    def _create_connection_frame(self, parent):
        """创建连接控制区"""
        frame = tk.Frame(parent, bg=self.COLORS['bg_medium'], padx=15, pady=15)
        frame.pack(fill=tk.X, pady=(0, 15))
        
        # 第一行：端口和波特率选择
        port_frame = tk.Frame(frame, bg=self.COLORS['bg_medium'])
        port_frame.pack(fill=tk.X)
        
        tk.Label(
            port_frame,
            text="串口:",
            font=('Microsoft YaHei UI', 11),
            fg=self.COLORS['text_primary'],
            bg=self.COLORS['bg_medium']
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(
            port_frame,
            textvariable=self.port_var,
            state='readonly',
            width=15,
            font=('Consolas', 10)
        )
        self.port_combo.pack(side=tk.LEFT, padx=(0, 10))
        
        refresh_btn = tk.Button(
            port_frame,
            text="刷新",
            font=('Microsoft YaHei UI', 10),
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
            font=('Microsoft YaHei UI', 11),
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
            font=('Consolas', 10)
        )
        baudrate_combo.pack(side=tk.LEFT, padx=(0, 20))
        
        # 连接按钮
        self.connect_btn = tk.Button(
            port_frame,
            text="连接",
            font=('Microsoft YaHei UI', 11, 'bold'),
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
            font=('Microsoft YaHei UI', 10),
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
            font=('Microsoft YaHei UI', 10),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        self.sim_interval_var = tk.StringVar(value='5')
        sim_interval_entry = tk.Entry(
            mode_frame,
            textvariable=self.sim_interval_var,
            width=5,
            font=('Consolas', 10),
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
            font=('Microsoft YaHei UI', 10),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        )
        self.status_label.pack(side=tk.LEFT, padx=(8, 0))
    
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
            font=('Microsoft YaHei UI', 14),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        ).pack()
        
        self.sys_value = tk.Label(
            sys_frame,
            text="---",
            font=('Segoe UI', 56, 'bold'),
            fg=self.COLORS['accent'],
            bg=self.COLORS['bg_medium']
        )
        self.sys_value.pack()
        
        tk.Label(
            sys_frame,
            text="mmHg",
            font=('Microsoft YaHei UI', 12),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        ).pack()
        
        # 舒张压
        dia_frame = tk.Frame(display_container, bg=self.COLORS['bg_medium'])
        dia_frame.grid(row=0, column=1, sticky='nsew', padx=10)
        
        tk.Label(
            dia_frame,
            text="舒张压",
            font=('Microsoft YaHei UI', 14),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        ).pack()
        
        self.dia_value = tk.Label(
            dia_frame,
            text="---",
            font=('Segoe UI', 56, 'bold'),
            fg=self.COLORS['accent_light'],
            bg=self.COLORS['bg_medium']
        )
        self.dia_value.pack()
        
        tk.Label(
            dia_frame,
            text="mmHg",
            font=('Microsoft YaHei UI', 12),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        ).pack()
        
        # 心率
        pr_frame = tk.Frame(display_container, bg=self.COLORS['bg_medium'])
        pr_frame.grid(row=0, column=2, sticky='nsew', padx=10)
        
        tk.Label(
            pr_frame,
            text="心率",
            font=('Microsoft YaHei UI', 14),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        ).pack()
        
        self.pr_value = tk.Label(
            pr_frame,
            text="---",
            font=('Segoe UI', 56, 'bold'),
            fg=self.COLORS['success'],
            bg=self.COLORS['bg_medium']
        )
        self.pr_value.pack()
        
        tk.Label(
            pr_frame,
            text="bpm",
            font=('Microsoft YaHei UI', 12),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        ).pack()
        
        self.update_time_label = tk.Label(
            frame,
            text="等待测量数据...",
            font=('Microsoft YaHei UI', 10),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        )
        self.update_time_label.pack(pady=(15, 0))
    
    def _create_history_frame(self, parent):
        """创建历史记录区"""
        frame = tk.Frame(parent, bg=self.COLORS['bg_medium'], padx=15, pady=15)
        frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        header_frame = tk.Frame(frame, bg=self.COLORS['bg_medium'])
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(
            header_frame,
            text="历史记录",
            font=('Microsoft YaHei UI', 12, 'bold'),
            fg=self.COLORS['text_primary'],
            bg=self.COLORS['bg_medium']
        ).pack(side=tk.LEFT)
        
        clear_btn = tk.Button(
            header_frame,
            text="清空",
            font=('Microsoft YaHei UI', 9),
            bg=self.COLORS['bg_light'],
            fg=self.COLORS['text_secondary'],
            activebackground=self.COLORS['danger'],
            activeforeground=self.COLORS['text_primary'],
            relief=tk.FLAT,
            cursor='hand2',
            command=self._clear_history
        )
        clear_btn.pack(side=tk.RIGHT)
        
        list_frame = tk.Frame(frame, bg=self.COLORS['bg_dark'])
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.history_listbox = tk.Listbox(
            list_frame,
            font=('Consolas', 11),
            bg=self.COLORS['bg_dark'],
            fg=self.COLORS['text_primary'],
            selectbackground=self.COLORS['accent'],
            selectforeground=self.COLORS['text_primary'],
            highlightthickness=0,
            relief=tk.FLAT,
            yscrollcommand=scrollbar.set
        )
        self.history_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.history_listbox.yview)
    
    def _create_log_frame(self, parent):
        """创建日志区"""
        self.log_expanded = tk.BooleanVar(value=False)
        
        toggle_frame = tk.Frame(parent, bg=self.COLORS['bg_dark'])
        toggle_frame.pack(fill=tk.X)
        
        self.toggle_log_btn = tk.Button(
            toggle_frame,
            text="▶ 显示原始数据日志（调试用）",
            font=('Microsoft YaHei UI', 9),
            bg=self.COLORS['bg_dark'],
            fg=self.COLORS['text_secondary'],
            activebackground=self.COLORS['bg_dark'],
            activeforeground=self.COLORS['text_primary'],
            relief=tk.FLAT,
            cursor='hand2',
            command=self._toggle_log
        )
        self.toggle_log_btn.pack(anchor='w')
        
        self.log_frame = tk.Frame(parent, bg=self.COLORS['bg_dark'])
        
        log_scrollbar = tk.Scrollbar(self.log_frame)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.log_text = tk.Text(
            self.log_frame,
            font=('Consolas', 9),
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
            self.toggle_log_btn.config(text="▶ 显示原始数据日志（调试用）")
            self.log_expanded.set(False)
        else:
            self.log_frame.pack(fill=tk.X, pady=(5, 0))
            self.toggle_log_btn.config(text="▼ 隐藏原始数据日志")
            self.log_expanded.set(True)
    
    def _refresh_ports(self):
        """刷新串口列表"""
        ports = SerialConnection.get_port_info()
        port_names = [p[0] for p in ports]
        
        self.port_combo['values'] = port_names
        if port_names:
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
                self.status_indicator.delete('all')
                self.status_indicator.create_oval(2, 2, 10, 10, fill=self.COLORS['simulation'], outline='')
                self.status_label.config(text="模拟模式", fg=self.COLORS['simulation'])
            else:
                self.connect_btn.config(text="断开", bg=self.COLORS['danger'], state='normal')
                self.sim_btn.config(state='disabled')
                self.status_indicator.delete('all')
                self.status_indicator.create_oval(2, 2, 10, 10, fill=self.COLORS['success'], outline='')
                self.status_label.config(text="已连接", fg=self.COLORS['success'])
        else:
            self.connect_btn.config(text="连接", bg=self.COLORS['success'], state='normal')
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
            elif value < 120:
                return self.COLORS['success']
            elif value < 140:
                return self.COLORS['warning']
            else:
                return self.COLORS['danger']
        else:
            if value < 60:
                return self.COLORS['warning']
            elif value < 80:
                return self.COLORS['success']
            elif value < 90:
                return self.COLORS['warning']
            else:
                return self.COLORS['danger']
    
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


def main():
    """主函数"""
    logger.info("启动 OMRON HBP-9030 血压监测程序")
    
    # 检查环境
    if not SERIAL_AVAILABLE:
        logger.warning("pyserial库未安装，将只能使用模拟模式")
    
    app = BloodPressureMonitorGUI()
    app.run()


if __name__ == '__main__':
    main()

```

现在让我改进模拟模式，让它**模拟真实的数据流程**（生成原始数据→解析→显示）：

```python
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
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import re
import random
import time
import os
import sys
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
    支持多种可能的数据格式
    """
    
    @staticmethod
    def parse(data: bytes) -> Optional[BloodPressureReading]:
        """
        尝试解析血压数据
        支持多种格式的自动识别
        """
        try:
            # 尝试不同的编码方式解码
            text = ""
            for encoding in ['ascii', 'utf-8', 'latin-1', 'gbk']:
                try:
                    text = data.decode(encoding).strip()
                    break
                except (UnicodeDecodeError, LookupError):
                    continue
            
            if not text:
                text = data.decode('ascii', errors='ignore').strip()
            
            if not text:
                return None
                
            logger.debug(f"接收原始数据: {repr(text)}")
            logger.debug(f"十六进制: {data.hex()}")
            
            # 尝试多种格式解析（按优先级顺序）
            # 如果你知道设备的确切格式，可以把对应的解析方法放在最前面
            result = (
                DataParser._parse_format_hbp9030(text) or  # HBP-9030专用格式（优先）
                DataParser._parse_format_csv(text) or
                DataParser._parse_format_space(text) or
                DataParser._parse_format_labeled(text) or
                DataParser._parse_format_numeric(text) or
                DataParser._parse_format_bytes(data)
            )
            
            if result:
                result.raw_data = text
                logger.info(f"解析成功: SYS={result.systolic}, DIA={result.diastolic}, PR={result.pulse}")
            
            return result
            
        except Exception as e:
            logger.error(f"解析数据时出错: {e}")
            return None
    
    @staticmethod
    def _parse_format_hbp9030(text: str) -> Optional[BloodPressureReading]:
        """
        HBP-9030 专用格式解析
        
        ============================================================
        【重要】请根据实际接收到的数据格式修改此方法！
        ============================================================
        
        当你连接真实设备后，展开"原始数据日志"查看实际格式，
        然后修改下面的解析逻辑。
        
        常见格式示例：
        1. STX,ID,YYYY,MM,DD,HH,MM,SYS,DIA,PR,ETX
           例: STX,001,2026,01,20,14,30,125,82,68,ETX
           
        2. 固定长度格式（每个字段固定宽度）
           例: 001202601201430125082068
           
        3. 带校验和的格式
           例: $BP,125,82,68*5A
        
        当前实现：尝试匹配 STX...ETX 格式，你可以根据实际情况修改
        """
        try:
            # === 格式1: STX,ID,YYYY,MM,DD,HH,MM,SYS,DIA,PR,ETX ===
            if 'STX' in text and 'ETX' in text:
                # 提取STX和ETX之间的内容
                start = text.find('STX')
                end = text.find('ETX')
                if start >= 0 and end > start:
                    content = text[start+3:end].strip(',')
                    parts = content.split(',')
                    # 假设最后3个数字是 SYS, DIA, PR
                    if len(parts) >= 3:
                        try:
                            sys_val = int(parts[-3])
                            dia_val = int(parts[-2])
                            pr_val = int(parts[-1])
                            if 60 <= sys_val <= 300 and 30 <= dia_val <= 200 and 30 <= pr_val <= 200:
                                if sys_val > dia_val:
                                    return BloodPressureReading(
                                        systolic=sys_val,
                                        diastolic=dia_val,
                                        pulse=pr_val,
                                        timestamp=datetime.now()
                                    )
                        except ValueError:
                            pass
            
            # === 格式2: 在这里添加其他格式的解析 ===
            # 例如固定长度格式:
            # if len(text) == 24:  # 固定24字符
            #     sys_val = int(text[15:18])
            #     dia_val = int(text[18:21])
            #     pr_val = int(text[21:24])
            #     ...
            
            # === 格式3: 带校验和格式 ===
            # if text.startswith('$BP,'):
            #     ...
            
        except Exception as e:
            logger.debug(f"HBP-9030格式解析失败: {e}")
        return None
    
    @staticmethod
    def _parse_format_csv(text: str) -> Optional[BloodPressureReading]:
        """解析CSV格式: 日期,时间,SYS,DIA,PR 或类似格式"""
        try:
            parts = text.split(',')
            if len(parts) >= 3:
                numbers = []
                for p in parts:
                    p = p.strip()
                    if p.isdigit():
                        numbers.append(int(p))
                
                for i in range(len(numbers) - 2):
                    sys_val, dia_val, pr_val = numbers[i], numbers[i+1], numbers[i+2]
                    if 60 <= sys_val <= 300 and 30 <= dia_val <= 200 and 30 <= pr_val <= 200:
                        if sys_val > dia_val:
                            return BloodPressureReading(
                                systolic=sys_val,
                                diastolic=dia_val,
                                pulse=pr_val,
                                timestamp=datetime.now()
                            )
        except Exception:
            pass
        return None
    
    @staticmethod
    def _parse_format_space(text: str) -> Optional[BloodPressureReading]:
        """解析空格分隔格式"""
        try:
            parts = text.split()
            numbers = [int(p) for p in parts if p.isdigit()]
            
            for i in range(len(numbers) - 2):
                sys_val, dia_val, pr_val = numbers[i], numbers[i+1], numbers[i+2]
                if 60 <= sys_val <= 300 and 30 <= dia_val <= 200 and 30 <= pr_val <= 200:
                    if sys_val > dia_val:
                        return BloodPressureReading(
                            systolic=sys_val,
                            diastolic=dia_val,
                            pulse=pr_val,
                            timestamp=datetime.now()
                        )
        except Exception:
            pass
        return None
    
    @staticmethod
    def _parse_format_labeled(text: str) -> Optional[BloodPressureReading]:
        """解析带标签格式: SYS:120 DIA:80 PR:72 等"""
        try:
            sys_match = re.search(r'(?:SYS|sys|收缩|高压)[:\s=]*(\d+)', text)
            dia_match = re.search(r'(?:DIA|dia|舒张|低压)[:\s=]*(\d+)', text)
            pr_match = re.search(r'(?:PR|pr|HR|hr|脉搏|心率|PULSE|pulse)[:\s=]*(\d+)', text)
            
            if sys_match and dia_match and pr_match:
                return BloodPressureReading(
                    systolic=int(sys_match.group(1)),
                    diastolic=int(dia_match.group(1)),
                    pulse=int(pr_match.group(1)),
                    timestamp=datetime.now()
                )
            
            bp_match = re.search(r'(\d{2,3})\s*/\s*(\d{2,3})\s+(\d{2,3})', text)
            if bp_match:
                return BloodPressureReading(
                    systolic=int(bp_match.group(1)),
                    diastolic=int(bp_match.group(2)),
                    pulse=int(bp_match.group(3)),
                    timestamp=datetime.now()
                )
        except Exception:
            pass
        return None
    
    @staticmethod
    def _parse_format_numeric(text: str) -> Optional[BloodPressureReading]:
        """解析纯数字格式"""
        try:
            numbers = re.findall(r'\d+', text)
            if len(numbers) >= 3:
                for i in range(len(numbers) - 2):
                    sys_val = int(numbers[i])
                    dia_val = int(numbers[i+1])
                    pr_val = int(numbers[i+2])
                    
                    if 60 <= sys_val <= 300 and 30 <= dia_val <= 200 and 30 <= pr_val <= 200:
                        if sys_val > dia_val:
                            return BloodPressureReading(
                                systolic=sys_val,
                                diastolic=dia_val,
                                pulse=pr_val,
                                timestamp=datetime.now()
                            )
        except Exception:
            pass
        return None
    
    @staticmethod
    def _parse_format_bytes(data: bytes) -> Optional[BloodPressureReading]:
        """解析二进制格式"""
        try:
            if len(data) >= 6:
                for offset in range(len(data) - 2):
                    sys_val = data[offset]
                    dia_val = data[offset + 1]
                    pr_val = data[offset + 2]
                    
                    if 60 <= sys_val <= 250 and 30 <= dia_val <= 150 and 30 <= pr_val <= 180:
                        if sys_val > dia_val:
                            return BloodPressureReading(
                                systolic=sys_val,
                                diastolic=dia_val,
                                pulse=pr_val,
                                timestamp=datetime.now()
                            )
        except Exception:
            pass
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
        """
        模拟数据生成循环
        
        模拟模式会生成类似真实设备的原始数据，然后通过DataParser解析，
        这样可以验证解析器是否能正确处理数据。
        
        你可以修改 simulate_format 来测试不同的数据格式。
        """
        # 模拟数据格式（可以修改这里来测试不同格式）
        simulate_format = "csv"  # 可选: "csv", "space", "labeled", "hbp9030"
        
        while self.is_running:
            # 生成随机但合理的血压数据
            sys_val = random.randint(100, 160)
            dia_val = random.randint(60, 100)
            pr_val = random.randint(55, 95)
            
            # 确保收缩压大于舒张压
            if dia_val >= sys_val:
                dia_val = sys_val - 20
            
            # 根据格式生成模拟的原始数据
            if simulate_format == "csv":
                # CSV格式: 120,80,72
                raw_text = f"{sys_val},{dia_val},{pr_val}"
            elif simulate_format == "space":
                # 空格分隔: 120 80 72
                raw_text = f"{sys_val} {dia_val} {pr_val}"
            elif simulate_format == "labeled":
                # 带标签: SYS:120 DIA:80 PR:72
                raw_text = f"SYS:{sys_val} DIA:{dia_val} PR:{pr_val}"
            elif simulate_format == "hbp9030":
                # HBP-9030格式: STX,001,2026,01,20,14,30,SYS,DIA,PR,ETX
                now = datetime.now()
                raw_text = f"STX,001,{now.year},{now.month:02d},{now.day:02d},{now.hour:02d},{now.minute:02d},{sys_val},{dia_val},{pr_val},ETX"
            else:
                raw_text = f"{sys_val},{dia_val},{pr_val}"
            
            raw_data = (raw_text + "\r\n").encode('ascii')
            
            # 显示原始数据到日志
            if self.on_raw_data:
                self.on_raw_data(raw_data)
            
            # 【关键】通过DataParser解析，模拟真实的数据处理流程
            reading = DataParser.parse(raw_data)
            
            if reading:
                reading.raw_data = f"[模拟-{simulate_format}] {raw_text}"
                if self.on_data_received:
                    self.on_data_received(reading)
                logger.info(f"[模拟] 生成并解析成功: {sys_val}/{dia_val} {pr_val}")
            else:
                logger.warning(f"[模拟] 生成的数据解析失败: {raw_text}")
            
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
        
        while self.is_running and self.serial_port and self.serial_port.is_open:
            try:
                if self.serial_port.in_waiting > 0:
                    data = self.serial_port.read(self.serial_port.in_waiting)
                    buffer += data
                    
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
        self.root.title("OMRON HBP-9030 血压监测")
        self.root.geometry("700x750")
        self.root.configure(bg=self.COLORS['bg_dark'])
        self.root.resizable(True, True)
        self.root.minsize(600, 650)
        
        # 设置窗口图标（如果有的话）
        try:
            # 尝试设置图标
            pass
        except Exception:
            pass
        
        # 数据
        self.readings: List[BloodPressureReading] = []
        self.data_queue = queue.Queue()
        self.simulation_mode = False
        
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
        main_frame = tk.Frame(self.root, bg=self.COLORS['bg_dark'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 标题
        title_label = tk.Label(
            main_frame,
            text="OMRON HBP-9030 血压监测",
            font=('Microsoft YaHei UI', 24, 'bold'),
            fg=self.COLORS['text_primary'],
            bg=self.COLORS['bg_dark']
        )
        title_label.pack(pady=(0, 20))
        
        # 连接控制区
        self._create_connection_frame(main_frame)
        
        # 血压显示区
        self._create_display_frame(main_frame)
        
        # 历史记录区
        self._create_history_frame(main_frame)
        
        # 日志区
        self._create_log_frame(main_frame)
    
    def _create_connection_frame(self, parent):
        """创建连接控制区"""
        frame = tk.Frame(parent, bg=self.COLORS['bg_medium'], padx=15, pady=15)
        frame.pack(fill=tk.X, pady=(0, 15))
        
        # 第一行：端口和波特率选择
        port_frame = tk.Frame(frame, bg=self.COLORS['bg_medium'])
        port_frame.pack(fill=tk.X)
        
        tk.Label(
            port_frame,
            text="串口:",
            font=('Microsoft YaHei UI', 11),
            fg=self.COLORS['text_primary'],
            bg=self.COLORS['bg_medium']
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(
            port_frame,
            textvariable=self.port_var,
            state='readonly',
            width=15,
            font=('Consolas', 10)
        )
        self.port_combo.pack(side=tk.LEFT, padx=(0, 10))
        
        refresh_btn = tk.Button(
            port_frame,
            text="刷新",
            font=('Microsoft YaHei UI', 10),
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
            font=('Microsoft YaHei UI', 11),
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
            font=('Consolas', 10)
        )
        baudrate_combo.pack(side=tk.LEFT, padx=(0, 20))
        
        # 连接按钮
        self.connect_btn = tk.Button(
            port_frame,
            text="连接",
            font=('Microsoft YaHei UI', 11, 'bold'),
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
            font=('Microsoft YaHei UI', 10),
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
            font=('Microsoft YaHei UI', 10),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        self.sim_interval_var = tk.StringVar(value='5')
        sim_interval_entry = tk.Entry(
            mode_frame,
            textvariable=self.sim_interval_var,
            width=5,
            font=('Consolas', 10),
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
            font=('Microsoft YaHei UI', 10),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        )
        self.status_label.pack(side=tk.LEFT, padx=(8, 0))
    
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
            font=('Microsoft YaHei UI', 14),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        ).pack()
        
        self.sys_value = tk.Label(
            sys_frame,
            text="---",
            font=('Segoe UI', 56, 'bold'),
            fg=self.COLORS['accent'],
            bg=self.COLORS['bg_medium']
        )
        self.sys_value.pack()
        
        tk.Label(
            sys_frame,
            text="mmHg",
            font=('Microsoft YaHei UI', 12),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        ).pack()
        
        # 舒张压
        dia_frame = tk.Frame(display_container, bg=self.COLORS['bg_medium'])
        dia_frame.grid(row=0, column=1, sticky='nsew', padx=10)
        
        tk.Label(
            dia_frame,
            text="舒张压",
            font=('Microsoft YaHei UI', 14),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        ).pack()
        
        self.dia_value = tk.Label(
            dia_frame,
            text="---",
            font=('Segoe UI', 56, 'bold'),
            fg=self.COLORS['accent_light'],
            bg=self.COLORS['bg_medium']
        )
        self.dia_value.pack()
        
        tk.Label(
            dia_frame,
            text="mmHg",
            font=('Microsoft YaHei UI', 12),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        ).pack()
        
        # 心率
        pr_frame = tk.Frame(display_container, bg=self.COLORS['bg_medium'])
        pr_frame.grid(row=0, column=2, sticky='nsew', padx=10)
        
        tk.Label(
            pr_frame,
            text="心率",
            font=('Microsoft YaHei UI', 14),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        ).pack()
        
        self.pr_value = tk.Label(
            pr_frame,
            text="---",
            font=('Segoe UI', 56, 'bold'),
            fg=self.COLORS['success'],
            bg=self.COLORS['bg_medium']
        )
        self.pr_value.pack()
        
        tk.Label(
            pr_frame,
            text="bpm",
            font=('Microsoft YaHei UI', 12),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        ).pack()
        
        self.update_time_label = tk.Label(
            frame,
            text="等待测量数据...",
            font=('Microsoft YaHei UI', 10),
            fg=self.COLORS['text_secondary'],
            bg=self.COLORS['bg_medium']
        )
        self.update_time_label.pack(pady=(15, 0))
    
    def _create_history_frame(self, parent):
        """创建历史记录区"""
        frame = tk.Frame(parent, bg=self.COLORS['bg_medium'], padx=15, pady=15)
        frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        header_frame = tk.Frame(frame, bg=self.COLORS['bg_medium'])
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(
            header_frame,
            text="历史记录",
            font=('Microsoft YaHei UI', 12, 'bold'),
            fg=self.COLORS['text_primary'],
            bg=self.COLORS['bg_medium']
        ).pack(side=tk.LEFT)
        
        clear_btn = tk.Button(
            header_frame,
            text="清空",
            font=('Microsoft YaHei UI', 9),
            bg=self.COLORS['bg_light'],
            fg=self.COLORS['text_secondary'],
            activebackground=self.COLORS['danger'],
            activeforeground=self.COLORS['text_primary'],
            relief=tk.FLAT,
            cursor='hand2',
            command=self._clear_history
        )
        clear_btn.pack(side=tk.RIGHT)
        
        list_frame = tk.Frame(frame, bg=self.COLORS['bg_dark'])
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.history_listbox = tk.Listbox(
            list_frame,
            font=('Consolas', 11),
            bg=self.COLORS['bg_dark'],
            fg=self.COLORS['text_primary'],
            selectbackground=self.COLORS['accent'],
            selectforeground=self.COLORS['text_primary'],
            highlightthickness=0,
            relief=tk.FLAT,
            yscrollcommand=scrollbar.set
        )
        self.history_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.history_listbox.yview)
    
    def _create_log_frame(self, parent):
        """创建日志区"""
        self.log_expanded = tk.BooleanVar(value=False)
        
        toggle_frame = tk.Frame(parent, bg=self.COLORS['bg_dark'])
        toggle_frame.pack(fill=tk.X)
        
        self.toggle_log_btn = tk.Button(
            toggle_frame,
            text="▶ 显示原始数据日志（调试用）",
            font=('Microsoft YaHei UI', 9),
            bg=self.COLORS['bg_dark'],
            fg=self.COLORS['text_secondary'],
            activebackground=self.COLORS['bg_dark'],
            activeforeground=self.COLORS['text_primary'],
            relief=tk.FLAT,
            cursor='hand2',
            command=self._toggle_log
        )
        self.toggle_log_btn.pack(anchor='w')
        
        self.log_frame = tk.Frame(parent, bg=self.COLORS['bg_dark'])
        
        log_scrollbar = tk.Scrollbar(self.log_frame)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.log_text = tk.Text(
            self.log_frame,
            font=('Consolas', 9),
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
            self.toggle_log_btn.config(text="▶ 显示原始数据日志（调试用）")
            self.log_expanded.set(False)
        else:
            self.log_frame.pack(fill=tk.X, pady=(5, 0))
            self.toggle_log_btn.config(text="▼ 隐藏原始数据日志")
            self.log_expanded.set(True)
    
    def _refresh_ports(self):
        """刷新串口列表"""
        ports = SerialConnection.get_port_info()
        port_names = [p[0] for p in ports]
        
        self.port_combo['values'] = port_names
        if port_names:
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
                self.status_indicator.delete('all')
                self.status_indicator.create_oval(2, 2, 10, 10, fill=self.COLORS['simulation'], outline='')
                self.status_label.config(text="模拟模式", fg=self.COLORS['simulation'])
            else:
                self.connect_btn.config(text="断开", bg=self.COLORS['danger'], state='normal')
                self.sim_btn.config(state='disabled')
                self.status_indicator.delete('all')
                self.status_indicator.create_oval(2, 2, 10, 10, fill=self.COLORS['success'], outline='')
                self.status_label.config(text="已连接", fg=self.COLORS['success'])
        else:
            self.connect_btn.config(text="连接", bg=self.COLORS['success'], state='normal')
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
            elif value < 120:
                return self.COLORS['success']
            elif value < 140:
                return self.COLORS['warning']
            else:
                return self.COLORS['danger']
        else:
            if value < 60:
                return self.COLORS['warning']
            elif value < 80:
                return self.COLORS['success']
            elif value < 90:
                return self.COLORS['warning']
            else:
                return self.COLORS['danger']
    
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


def main():
    """主函数"""
    logger.info("启动 OMRON HBP-9030 血压监测程序")
    
    # 检查环境
    if not SERIAL_AVAILABLE:
        logger.warning("pyserial库未安装，将只能使用模拟模式")
    
    app = BloodPressureMonitorGUI()
    app.run()


if __name__ == '__main__':
    main()

```

很好！现在让我为你总结一下改进的内容和如何修改：

## 总结

### 改进后的数据处理流程

```
                    ┌─────────────────────────────┐
                    │      真实设备/模拟器         │
                    └──────────────┬──────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────┐
                    │    原始字节数据 (bytes)      │
                    │  例: b'120,80,72\r\n'       │
                    └──────────────┬──────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────┐
                    │     DataParser.parse()      │
                    │   依次尝试6种格式解析        │
                    └──────────────┬──────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                    ▼
      _parse_format_hbp9030  _parse_format_csv    ... 其他格式
         (优先尝试)
                                   │
                                   ▼
                    ┌─────────────────────────────┐
                    │   BloodPressureReading      │
                    │   显示到界面                 │
                    └─────────────────────────────┘
```

### 如果实际格式不同，修改哪里

**主要修改 `_parse_format_hbp9030` 方法（第133-193行）**：

```python
@staticmethod
def _parse_format_hbp9030(text: str) -> Optional[BloodPressureReading]:
    """
    HBP-9030 专用格式解析
    
    【重要】请根据实际接收到的数据格式修改此方法！
    
    步骤：
    1. 连接真实设备
    2. 展开"原始数据日志"查看实际数据格式
    3. 根据格式修改下面的解析代码
    """
    try:
        # 根据你看到的实际格式，修改这里的解析逻辑
        # 例如，如果格式是固定位置的：
        # sys_val = int(text[10:13])  # 第10-12位是收缩压
        # dia_val = int(text[13:16])  # 第13-15位是舒张压
        # pr_val = int(text[16:19])   # 第16-18位是心率
        pass
    except Exception:
        pass
    return None
```

### 模拟模式改进

现在模拟模式**会走完整的解析流程**：

1. 生成模拟的原始数据字符串
2. 通过 `DataParser.parse()` 解析
3. 如果解析成功才显示

你可以修改 `simulate_format` 变量来测试不同格式：
- `"csv"` → `120,80,72`
- `"space"` → `120 80 72`
- `"labeled"` → `SYS:120 DIA:80 PR:72`
- `"hbp9030"` → `STX,001,2026,01,20,14,30,120,80,72,ETX`

### 调试建议

当你拿到真实设备后：

1. **启动程序，连接设备**
2. **展开"原始数据日志"**
3. **进行一次测量**
4. **观察日志中显示的原始数据格式**
5. **根据实际格式修改 `_parse_format_hbp9030` 方法**

日志会同时记录到 `bp_monitor.log` 文件，你可以把这个文件发给我，我帮你写对应的解析代码。

```plaintext
                    ┌─────────────────────────────┐
                    │      真实设备/模拟器         │
                    └──────────────┬──────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────┐
                    │    原始字节数据 (bytes)      │
                    │  例: b'120,80,72\r\n'       │
                    └──────────────┬──────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────┐
                    │     DataParser.parse()      │
                    │   依次尝试6种格式解析        │
                    └──────────────┬──────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                    ▼
      _parse_format_hbp9030  _parse_format_csv    ... 其他格式
         (优先尝试)
                                   │
                                   ▼
                    ┌─────────────────────────────┐
                    │   BloodPressureReading      │
                    │   显示到界面                 │
                    └─────────────────────────────┘
```

```python
@staticmethod
def _parse_format_hbp9030(text: str) -> Optional[BloodPressureReading]:
    """
    HBP-9030 专用格式解析
    
    【重要】请根据实际接收到的数据格式修改此方法！
    
    步骤：
    1. 连接真实设备
    2. 展开"原始数据日志"查看实际数据格式
    3. 根据格式修改下面的解析代码
    """
    try:
        # 根据你看到的实际格式，修改这里的解析逻辑
        # 例如，如果格式是固定位置的：
        # sys_val = int(text[10:13])  # 第10-12位是收缩压
        # dia_val = int(text[13:16])  # 第13-15位是舒张压
        # pr_val = int(text[16:19])   # 第16-18位是心率
        pass
    except Exception:
        pass
    return None
```

```plaintext
                    ┌─────────────────────────────┐
                    │      真实设备/模拟器         │
                    └──────────────┬──────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────┐
                    │    原始字节数据 (bytes)      │
                    │  例: b'120,80,72\r\n'       │
                    └──────────────┬──────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────┐
                    │     DataParser.parse()      │
                    │   依次尝试6种格式解析        │
                    └──────────────┬──────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                    ▼
      _parse_format_hbp9030  _parse_format_csv    ... 其他格式
         (优先尝试)
                                   │
                                   ▼
                    ┌─────────────────────────────┐
                    │   BloodPressureReading      │
                    │   显示到界面                 │
                    └─────────────────────────────┘
```

```python
@staticmethod
def _parse_format_hbp9030(text: str) -> Optional[BloodPressureReading]:
    """
    HBP-9030 专用格式解析
    
    【重要】请根据实际接收到的数据格式修改此方法！
    
    步骤：
    1. 连接真实设备
    2. 展开"原始数据日志"查看实际数据格式
    3. 根据格式修改下面的解析代码
    """
    try:
        # 根据你看到的实际格式，修改这里的解析逻辑
        # 例如，如果格式是固定位置的：
        # sys_val = int(text[10:13])  # 第10-12位是收缩压
        # dia_val = int(text[13:16])  # 第13-15位是舒张压
        # pr_val = int(text[16:19])   # 第16-18位是心率
        pass
    except Exception:
        pass
    return None
```

