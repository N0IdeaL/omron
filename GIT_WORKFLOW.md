# Git 分支管理与部署策略

## 推荐的分支结构

```
main (或 master)           # 稳定版本，生产就绪
  │
  ├── develop              # 开发分支，最新功能
  │     │
  │     ├── feature/xxx    # 功能分支
  │     └── bugfix/xxx     # 修复分支
  │
  ├── release/windows      # Windows 发布版本
  └── release/raspberry-pi # 树莓派发布版本
```

## 分支说明

| 分支 | 用途 | 部署目标 |
|------|------|----------|
| `main` | 稳定代码，跨平台通用 | 所有平台 |
| `develop` | 日常开发 | 开发测试 |
| `release/windows` | Windows专用配置 | 医院Windows电脑 |
| `release/raspberry-pi` | 树莓派专用配置 | 树莓派设备 |

## 常用Git命令

### 初始化仓库
```bash
git init
git add .
git commit -m "初始版本"
```

### 创建开发分支
```bash
git checkout -b develop
```

### 创建功能分支
```bash
git checkout develop
git checkout -b feature/new-parser   # 例如：添加新的数据解析格式
```

### 合并功能到开发分支
```bash
git checkout develop
git merge feature/new-parser
git branch -d feature/new-parser     # 删除功能分支
```

### 创建发布分支
```bash
# Windows 发布分支
git checkout main
git checkout -b release/windows

# 树莓派发布分支
git checkout main
git checkout -b release/raspberry-pi
```

### 从 main 更新发布分支
```bash
git checkout release/windows
git merge main

git checkout release/raspberry-pi
git merge main
```

## 部署流程

### Windows 部署
```bash
git checkout release/windows
# 运行打包脚本
build.bat
# 将 dist/血压监测程序.exe 发送到目标电脑
```

### 树莓派部署
```bash
git checkout release/raspberry-pi
# 复制到树莓派
scp -r . pi@raspberrypi:~/bp_monitor/
# SSH 到树莓派运行安装脚本
ssh pi@raspberrypi "cd ~/bp_monitor && sudo bash install_raspberry_pi.sh"
```

## 针对不同平台的配置差异

当前代码已经做了**自动平台检测**，大部分情况下不需要维护不同的代码分支。

但如果需要平台特定的配置，可以：

### 方法1：使用配置文件（推荐）
创建 `config_windows.json` 和 `config_raspberry_pi.json`，程序自动加载对应配置。

### 方法2：使用分支隔离
在 `release/windows` 和 `release/raspberry-pi` 分支中做平台特定修改。

### 方法3：环境变量
```bash
# Windows
set BP_FULLSCREEN=false
python bp_monitor.py

# 树莓派
export BP_FULLSCREEN=true
python3 bp_monitor.py
```

## 当前代码的跨平台特性

代码中的 `PlatformConfig` 类会自动检测：

- **Windows**: 使用 Microsoft YaHei UI 字体，COM端口
- **Linux/树莓派**: 使用 Noto Sans CJK SC 字体，/dev/tty* 端口
- **树莓派特殊处理**: 小屏幕适配，默认全屏，字体缩小

无需为不同平台维护不同代码，一套代码即可运行在所有平台。

## 最佳实践

1. **日常开发**在 `develop` 分支进行
2. **功能稳定后**合并到 `main`
3. **发布前**从 `main` 合并到对应的 `release/*` 分支
4. **平台特定修改**只在 `release/*` 分支进行
5. **通用修复**在 `main` 修改后合并到所有分支

