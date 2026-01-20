#!/bin/bash
# ============================================
#  OMRON HBP-9030 血压监测程序 - 树莓派安装脚本
# ============================================

set -e

echo "============================================"
echo "  OMRON HBP-9030 血压监测程序 - 树莓派安装"
echo "============================================"
echo ""

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then
    echo "请使用 sudo 运行此脚本"
    echo "用法: sudo bash install_raspberry_pi.sh"
    exit 1
fi

# 获取实际用户名（非root）
ACTUAL_USER=${SUDO_USER:-$USER}
INSTALL_DIR="/home/$ACTUAL_USER/bp_monitor"

echo "[1/6] 更新系统包..."
apt-get update -qq

echo "[2/6] 安装Python3和Tkinter..."
apt-get install -y python3 python3-pip python3-tk

echo "[3/6] 安装中文字体支持..."
apt-get install -y fonts-wqy-microhei fonts-wqy-zenhei

echo "[4/6] 安装Python依赖..."
pip3 install pyserial

echo "[5/6] 设置串口权限..."
# 将用户添加到dialout组以访问串口
usermod -a -G dialout $ACTUAL_USER

echo "[6/6] 创建桌面快捷方式..."
# 创建安装目录
mkdir -p "$INSTALL_DIR"
cp bp_monitor.py "$INSTALL_DIR/"

# 创建桌面快捷方式
DESKTOP_FILE="/home/$ACTUAL_USER/Desktop/血压监测程序.desktop"
cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Name=血压监测程序
Comment=OMRON HBP-9030 血压监测
Exec=python3 $INSTALL_DIR/bp_monitor.py
Icon=utilities-system-monitor
Terminal=false
Type=Application
Categories=Utility;
EOF

chmod +x "$DESKTOP_FILE"
chown $ACTUAL_USER:$ACTUAL_USER "$DESKTOP_FILE"
chown -R $ACTUAL_USER:$ACTUAL_USER "$INSTALL_DIR"

echo ""
echo "============================================"
echo "  安装完成!"
echo "============================================"
echo ""
echo "程序已安装到: $INSTALL_DIR"
echo "桌面快捷方式: $DESKTOP_FILE"
echo ""
echo "【重要提示】"
echo "1. 请重启树莓派或重新登录以使串口权限生效"
echo "2. 连接血压计USB后，串口通常为 /dev/ttyUSB0 或 /dev/ttyACM0"
echo "3. 双击桌面上的「血压监测程序」图标启动"
echo ""
echo "手动运行方式:"
echo "  python3 $INSTALL_DIR/bp_monitor.py"
echo ""

