@echo off
chcp 65001 >nul
echo ============================================
echo    OMRON HBP-9030 血压监测程序_B - 打包工具
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

:: 安装依赖（B版本需要requests）
echo.
echo [2/4] 安装依赖包...
pip install requests pyinstaller -q

if errorlevel 1 (
    echo [错误] 安装依赖失败
    pause
    exit /b 1
)

echo      依赖安装完成

:: 打包
echo.
echo [3/4] 开始打包程序_B...
echo      这可能需要1-3分钟，请耐心等待...
echo.

pyinstaller ^
  --onefile ^
  --windowed ^
  --name "血压监测程序_b" ^
  --clean ^
  --noconfirm ^
  --distpath "dist_b" ^
  --workpath "build_b" ^
  --specpath "build_b" ^
  bp_monitor_b.py

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
echo   dist_b\血压监测程序_b.exe
echo.
echo 你可以将这个exe文件复制到任何Windows电脑上运行
echo 无需安装Python或任何依赖
echo ============================================
echo.

:: 打开输出目录
explorer dist_b

pause


