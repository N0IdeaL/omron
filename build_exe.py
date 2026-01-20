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

