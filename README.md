# Auto Mod Classifier V3

> Minecraft **客户端->服务端** 转换工具

[![Forked from](https://img.shields.io/badge/Forked%20from-qk--yiyihehe/auto--mod--classifier-blue)](https://github.com/qk-yiyihehe/auto-mod-classifier)

## 项目概述

本项目是基于 [qk-yiyihehe/auto-mod-classifier](https://github.com/qk-yiyihehe/auto-mod-classifier) fork 后的二次开发版本，在原项目基础上进行了功能增强和问题修复。

Auto Mod Classifier（自动筛选模组分类器）是一款使用Python 3.x + PySide6 + qfluentwidgets构建的面向 Minecraft 服务端转换工具，旨在解决两大核心痛点：

1. **模组智能分类**：自动将客户端模组划分为「服务端保留」「纯客户端」「待人工确认」三类，减少人工审核工作量
2. **服务端一键构建**：从客户端实例目录、`mrpack` 或 `zip` 整合包直接生成可用服务端，自动化完成版本识别、依赖下载、Java 适配与启动验证等流程

相比 V2 版本，V3 对界面、模组筛选、服务端构建、下载链路、Java 适配和报错诊断等模块进行了全面重构，显著提升了性能、稳定性和用户体验。

### 二次开发变更

本 fork 版本在原项目基础上新增了以下改进：

| 变更类型 | 描述 |
|----------|------|
| **Bug 修复** | Java 版本匹配逻辑优化，支持高版本 Java 向下兼容运行（如 Java 21 运行 Minecraft 1.20.1） |
| **Bug 修复** | 设置文件路径修复，确保设置在程序重启后正确保存和加载 |
| **功能增强** | 添加华为云 OpenJDK 镜像源支持，加速国内用户 Java 自动下载速度 |

## 核心功能

### 模组筛选

| 特性 | 说明 |
|------|------|
| 智能分类 | 自动识别模组类型，分为「服务端保留」「纯客户端」「待人工确认」三类 |
| 多加载器支持 | 原生支持 Fabric / Quilt / Forge / NeoForge |
| 多源查询 | 优先读取模组元数据，依次查询本地离线库、Modrinth、MC百科、CurseForge |
| 离线优先 | 支持本地 SQLite 数据库优先命中，减少联网依赖 |
| 结果导出 | 支持 CSV / JSON / TXT 报告格式，并提供可视化结果预览 |
| 性能指标 | 实测 300 个模组筛选耗时约 2 分钟，较 V2 提升 3 倍以上 |

### 一键构建服务端

| 特性 | 说明 |
|------|------|
| 多源导入 | 支持客户端实例目录、`mrpack` 整合包、`zip` 整合包直接导入 |
| 版本识别 | 自动识别 Minecraft 版本、加载器类型及精确版本号 |
| 自动下载 | 自动下载安装器、服务端依赖及必要文件 |
| 模组复制 | 自动筛选并复制服务端兼容的模组及配置目录 |
| Java 适配 | 自动检测本机 Java 版本，支持高版本兼容回退；缺失时自动下载 |
| 启动验证 | 自动写入 `eula=true` 并执行首次启动验证 |

### 开服失败诊断

- 常见问题类型自动判断（依赖缺失、版本不匹配、纯客户端模组混入、Java 版本错误）
- 关键报错片段智能提取与整理
- 支持一键复制错误日志，便于后续排查

### 下载加速

- **智能选源**：根据资源类型自动选择最优下载源
- **国内镜像**：内置 BMCLAPI、MCIM 及华为云 OpenJDK 镜像支持
- **自动回退**：主源失败时自动切换备用源，保障下载成功率


## 快速开始

### 通过源码运行

```powershell
pythonw .\自动筛选模组分类器.pyw
```

### 通过脚本运行

```text
启动自动筛选模组分类器.bat
```

### 打包为可执行文件

```text
打包.bat
```

打包后在 `dist` 目录生成可执行文件（如 `auto-mod-classifier-3.0.x.exe`）。

## 配置说明

### 下载源设置

| 选项 | 说明 |
|------|------|
| 智能优选 | 根据资源类型自动选择最优下载源 |
| 官方源 | 优先使用官方下载地址 |
| BMCLAPI 优先 | 优先使用 BMCLAPI 镜像（Mojang/Fabric/Forge 依赖） |
| MCIM 优先 | 优先使用 MCIM 镜像（Modrinth/CurseForge 模组） |

### Java 选择规则

- **自动匹配**：优先查找版本完全匹配的 Java，未找到时使用高版本兼容回退
- **优先使用本机 Java**：优先扫描系统已安装的 Java
- **只使用客户端自带 Java**：仅使用 `.minecraft/runtime` 中的 Java

> **注意**：Minecraft 1.20.1 及以下版本需要 Java 17，1.20.5+ 需要 Java 21。程序支持高版本 Java 向下兼容运行。

### 离线数据库

开启后优先查询本地 `db.sqlite` 数据库，显著提升分类速度并减少联网依赖。

## 使用建议

1. 若已部署离线模组库，建议优先开启本地库查询，速度更稳定
2. `mrpack` 和 `zip` 整合包可直接导入，无需通过启动器中转
3. 首次启动失败时，优先查看程序生成的诊断信息和关键报错片段
4. 一键构建服务端不会修改客户端源目录

## 注意事项

- Quilt 目前仅支持模组筛选识别，暂不支持自动构建服务端
- MC百科和部分 CurseForge 兜底查询依赖真实浏览器（推荐安装 Chrome 或 Edge）
- 联网筛选速度受网络环境影响，V3 已优化本地判断和多源查询顺序
- 整合包导入缓存保存在系统临时目录，程序关闭时自动清理

## 开发指南

### 环境要求

- Python 3.10+
- PySide6
- qfluentwidgets

### 安装依赖

```powershell
pip install -r requirements.txt
```

### 项目结构

```
auto-mod-classifier/
├── .github/workflows/             # GitHub CI 配置
├── auto_mod_classifier/           # 主程序目录
│   ├── application/               # 应用层（UseCase、模型、接口）
│   ├── classifier/                # 模组分类器核心
│   ├── infrastructure/            # 基础设施层
│   ├── server_builder/            # 服务端构建器核心
│   ├── ui/                        # Qt 界面层
│   ├── bootstrap.py               # 应用启动引导
│   ├── download_support.py        # 智能下载链路
│   ├── shared.py                  # 共享常量与工具函数
│   └── tasks.py                   # 任务执行入口
├── .gitignore                     # Git 忽略规则
├── README.md                      # 项目说明文档
├── requirements.txt               # Python 依赖列表
├── 自动筛选模组分类器.pyw          # 程序入口
├── 自动筛选模组分类器.ico          # 程序图标
├── 启动自动筛选模组分类器.bat      # 启动脚本
└── 打包发布.bat                   # 打包脚本
```

---

*Auto Mod Classifier — 让 Minecraft 服务端管理更高效*
