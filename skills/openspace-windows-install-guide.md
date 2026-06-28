---
name: openspace-windows-install-guide
description: OpenSpace 在 Windows 上安装接入 Claude Code 的完整指南，含踩坑记录与解决方案
metadata: 
  node_type: memory
  type: reference
  originSessionId: 381726a9-7a3a-460c-befe-657b583df759
---

# OpenSpace Windows 安装指南

> **项目**：[HKUDS/OpenSpace](https://github.com/HKUDS/OpenSpace) v0.1.0
> **适用平台**：Windows 10/11 + Claude Code
> **编写日期**：2026-06-24
> **验证环境**：Windows 10 Pro、Python 3.14.5、Node.js v25.0.0、Git Bash

---

## 目录

1. [安装前准备](#1-安装前准备)
2. [安装步骤](#2-安装步骤)
3. [Claude Code 接入配置](#3-claude-code-接入配置)
4. [Host Skills 部署](#4-host-skills-部署)
5. [Windows 特有问题与解决方案](#5-windows-特有问题与解决方案)
6. [验证安装](#6-验证安装)
7. [可选：本地仪表盘](#7-可选本地仪表盘)
8. [可选：云端社区](#8-可选云端社区)
9. [附录：配置文件速查](#9-附录配置文件速查)

---

## 1. 安装前准备

### 1.1 前置依赖

| 依赖 | 最低版本 | 说明 |
|------|----------|------|
| **Python** | 3.12+ | ⚠️ 建议使用 3.12 或 3.13，避免 3.14（过新可能有兼容风险） |
| **Node.js** | 20+ | 仅本地仪表盘需要 |
| **Git** | 任意 | 需包含 Git Bash（OpenSpace shell 后端依赖） |

### 1.2 确认 Git Bash 路径

OpenSpace 的 shell 后端默认使用 bash，Windows 上需要 Git Bash：

```bash
# 确认 Git Bash 存在
ls "C:/Git/bin/bash.exe"
# 或
where bash
```

> **记下这个路径**，后面配置要用。通常是 `C:/Git/bin/bash.exe`。

---

## 2. 安装步骤

### 2.1 克隆仓库

```bash
# 方式一：完整克隆（含 assets，约 50+ MB 图片）
git clone https://github.com/HKUDS/OpenSpace.git && cd OpenSpace

# 方式二（推荐）：稀疏克隆，跳过 assets 大文件
git clone --filter=blob:none --sparse https://github.com/HKUDS/OpenSpace.git
cd OpenSpace
git sparse-checkout set --no-cone '/*' '!/assets/'
```

### 2.2 安装 Python 包

```bash
pip install -e .
```

### 2.3 验证 CLI 可用

```bash
openspace-mcp --help
# 捕获成功任务为Skill
openspace capture --task "任务描述" --output skill-name

# 查看已沉淀技能
openspace skill list

# 技能进化（自动优化）
openspace evolve --skill skill-name

# 查看进化历史
openspace history --skill skill-name

# 批量优化Token消耗
openspace optimize --all-skills

# 启动自我进化引擎
openspace engine start

```

> ⚠️ **Windows 特殊行为**：`openspace-mcp --help` **不会输出任何内容**，但退出码为 0。这不是 bug —— `openspace-mcp` 是 MCP 协议服务器（stdio 模式），它不实现 argparse/click 的帮助系统，而是直接启动 JSON-RPC 协议循环等待 stdin 输入。**只要退出码为 0 就说明安装成功。**

```bash
# 正确的验证方式
openspace-mcp --help; echo "EXIT: $?"
# 期望输出：EXIT: 0（无 stdout 属正常行为）
```

---

## 3. Claude Code 接入配置

### 3.1 在 `~/.claude.json` 中注册 MCP Server

打开 `C:\Users\<你的用户名>\.claude.json`，在 `mcpServers` 中添加：

```json
{
  "mcpServers": {
    "openspace": {
      "command": "openspace-mcp",
      "toolTimeout": 600,
      "env": {
        "OPENSPACE_HOST_SKILL_DIRS": "C:/Users/<你的用户名>/.claude/skills",
        "OPENSPACE_WORKSPACE": "C:/Users/<你的用户名>/OpenSpace",
        "OPENSPACE_MODEL": "<你的模型ID>",
        "OPENSPACE_LLM_API_BASE": "<你的LLM端点>",
        "OPENSPACE_LLM_API_KEY": "<你的API密钥>"
      }
    }
  }
}
```

### 3.2 环境变量说明

| 变量 | 必填 | 说明 | 示例 |
|------|------|------|------|
| `OPENSPACE_HOST_SKILL_DIRS` | ✅ | Agent 的 Skill 目录 | `C:/Users/xxx/.claude/skills` |
| `OPENSPACE_WORKSPACE` | ✅ | OpenSpace 源码路径 | `C:/Users/xxx/OpenSpace` |
| `OPENSPACE_MODEL` | ✅ | LiteLLM 格式的模型 ID | `openai/xxx/xxx-glm-5` |
| `OPENSPACE_LLM_API_BASE` | ✅ | LLM API 端点 | `https://your-litellm-endpoint/v1` |
| `OPENSPACE_LLM_API_KEY` | ✅ | LLM API 密钥 | `sk-xxx` |
| `OPENSPACE_API_KEY` | ❌ | 云端社区密钥（上传 Skill 需要） | `sk-xxx` |

> **路径格式**：Windows 路径在 JSON 中**使用正斜杠** `/`，不要用反斜杠 `\`。正斜杠在 Windows 上与 Python 完全兼容，且避免 JSON 转义问题。

---

## 4. Host Skills 部署

将 OpenSpace 自带的两个宿主 Skill 复制到 Claude Code 的 skills 目录：

```bash
# 确保 skills 目录存在
mkdir -p ~/.claude/skills

# 复制 host skills
cp -r OpenSpace/openspace/host_skills/delegate-task/ ~/.claude/skills/
cp -r OpenSpace/openspace/host_skills/skill-discovery/ ~/.claude/skills/
```

| Skill | 教会 Agent 什么 |
|-------|-----------------|
| **delegate-task** | 何时委托 OpenSpace 执行任务、修复 Skill、上传 Skill |
| **skill-discovery** | 搜索与发现可用 Skill（本地 + 云端） |

---

## 5. Windows 特有问题与解决方案

> ⚡ 以下是实际安装过程中踩过的坑，按遇到顺序排列。

### 问题 1：`openspace-mcp --help` 无任何输出

| 项 | 详情 |
|----|------|
| **现象** | 执行 `openspace-mcp --help` 后无 stdout、无 stderr、无报错 |
| **原因** | `openspace-mcp` 是 stdio 模式的 MCP 服务器，入口函数 `run_mcp_server` 直接启动 JSON-RPC 协议循环，不实现 argparse/click 的帮助系统。在交互终端中，它会尝试启动 SSE 服务器（默认 127.0.0.1:8080），而非打印帮助文本 |
| **解决** | 这**不是 bug**，是设计行为。用退出码验证：`openspace-mcp --help; echo $?` 期望输出 `0` |

### 问题 2：找不到 MCP 注册配置

| 项 | 详情 |
|----|------|
| **现象** | 在 `~/.claude/settings.json`、`~/.claude/settings.local.json`、项目级 `.mcp.json` 中均找不到 openspace 的注册 |
| **原因** | Claude Code 的 MCP Server 注册在 **`~/.claude.json`**（全局主配置文件），**不在** `settings.json` 或 `.mcp.json` 中 |
| **解决** | 编辑 `C:\Users\<用户名>\.claude.json`，在 `mcpServers` 键下添加 `openspace` 配置（见[第 3 节](#3-claude-code-接入配置)） |

### 问题 3：配置文件仅存在 `.example` 模板

| 项 | 详情 |
|----|------|
| **现象** | `openspace/config/` 下 `config_communication.json`、`config_mcp.json`、`config_dev.json` 等文件不存在，只有 `.example` 后缀的模板 |
| **原因** | OpenSpace 采用 `.example` 模板机制，用户需手动复制激活 |
| **解决** | 核心配置文件 `config_grounding.json`、`config_agents.json`、`config_security.json` 已默认存在（无 `.example` 后缀），**这三个已够用**。其余可选配置按需复制： |

```bash
# 按需激活（非必须）
cd OpenSpace/openspace/config/
cp config_mcp.json.example config_mcp.json
cp config_communication.json.example config_communication.json
```

### 问题 4：Shell 后端使用 `/bin/bash` 导致全部命令返回 "unknown error"

| 项 | 详情 |
|----|------|
| **现象** | `execute_task` 执行任何 shell 命令（echo、python -c、dir 等）均返回 `"unknown error"`，无 stdout。OpenSpace 自动进化出 `no-success-no-complete` 和 `diagnose-shell-failure` 两个 Skill 来应对此故障 |
| **根因** | `config_grounding.json` 中 `default_shell` 默认值为 `"/bin/bash"`，这是 Linux 路径，在 Windows 上不存在 |
| **解决** | 修改 `openspace/config/config_grounding.json`，将 `default_shell` 改为 Windows 上 Git Bash 的路径 |

```json
// 修改前（Linux 默认）
"default_shell": "/bin/bash"

// 修改后（Windows Git Bash 路径，注意使用正斜杠）
"default_shell": "C:/Git/bin/bash.exe"
```

> ⚠️ **路径必须使用正斜杠** `/`，不要用 `\\`。反斜杠在 JSON 中需要双重转义，容易出错且部分 Python 库解析异常。

### 问题 5：修改配置后服务未生效

| 项 | 详情 |
|----|------|
| **现象** | 修改 `config_grounding.json` 后，OpenSpace MCP 服务仍使用旧配置 |
| **原因** | MCP Server 作为 Claude Code 的子进程常驻运行，配置文件在启动时加载，修改后不会自动重载 |
| **解决** | 需要重启 OpenSpace MCP 进程 |

```bash
# 1. 找到进程 PID
tasklist | grep -i python

# 2. 终止进程（通过 PID 或命令行匹配）
taskkill /F /PID <PID>

# 3. 重启 Claude Code 会话，MCP Server 会自动拉起
```

> 更优雅的方式：先轮转日志文件，再杀进程，再重启 Claude Code 会话观察新日志。

### 问题 6：Health Check 端点无响应

| 项 | 详情 |
|----|------|
| **现象** | 对 `http://localhost:8080/health` 或 `http://localhost:8765/health` 发起请求超时 |
| **原因** | stdio 模式的 MCP Server 不监听 HTTP 端口，health endpoint 仅在 SSE/streamable-http 传输模式下可用 |
| **解决** | **stdio 模式下无需 health check**。验证 MCP 连接是否正常，直接调用 MCP 工具即可（见[第 6 节](#6-验证安装)） |

### 问题 7：缺少 `websockets` 依赖导致 MCP WebSocket connector 无法工作

| 项 | 详情 |
|----|------|
| **现象** | 使用 SSE 或 streamable-http 传输模式时，或调用需要 WebSocket connector 的 MCP 后端时报 `ModuleNotFoundError: No module named 'websockets'` |
| **根因** | OpenSpace 的 `openspace/grounding/backends/mcp/transport/connectors/websocket.py:14` 直接引用 `from websockets import ClientConnection`，但 **`pyproject.toml` 的 `dependencies` 列表中未声明 `websockets`**。当前环境中 `websockets` 仅因 `mcp` 包的间接依赖而存在，如果 `mcp` 未来版本移除该依赖，OpenSpace 就会崩溃 |
| **解决** | 手动安装 `websockets` 包 |

```bash
pip install websockets
```

> **长期建议**：向 OpenSpace 项目提交 PR，在 `pyproject.toml` 的 `dependencies` 中添加 `"websockets>=10.0"`，确保该依赖被显式声明而非依赖间接引入。

### 问题 8：Windows 上 stdio 死锁（已知问题）

| 项 | 详情 |
|----|------|
| **现象** | MCP Server 进程卡死，不响应任何工具调用 |
| **原因** | Windows 上 stdio 管道在特定缓冲条件下可能死锁（项目 README 已记录 2026-03-27 修复，但某些环境可能仍有残留） |
| **解决** | 如频繁发生，可改用 SSE 或 streamable-http 传输模式作为替代 |

```bash
# 方式一：SSE 模式
openspace-mcp --transport sse --host 127.0.0.1 --port 8080
# 端点：http://127.0.0.1:8080/sse

# 方式二：streamable HTTP 模式
openspace-mcp --transport streamable-http --host 127.0.0.1 --port 8081
# 端点：http://127.0.0.1:8081/mcp
```

对应 Claude Code 配置改为：
```json
"openspace": {
  "type": "sse",
  "url": "http://127.0.0.1:8080/sse",
  "toolTimeout": 600
}
```

---

## 6. 验证安装

### 6.1 验证清单

| # | 验证项 | 方法 | 期望结果 |
|---|--------|------|----------|
| 1 | Python 包已安装 | `pip show openspace` | 显示版本 0.1.0 |
| 2 | CLI 可执行 | `openspace-mcp --help; echo $?` | 退出码 0（无输出属正常） |
| 3 | MCP 配置已注册 | 检查 `~/.claude.json` 中 `mcpServers.openspace` | 非空 |
| 4 | Shell 配置正确 | 检查 `config_grounding.json` 中 `default_shell` | 指向有效 bash 路径 |
| 5 | Host Skills 已复制 | `ls ~/.claude/skills/delegate-task/SKILL.md` | 文件存在 |
| 6 | MCP 连接正常 | 在 Claude Code 中调用 `search_skills` | 返回 Skill 列表 |

### 6.2 在 Claude Code 中验证

在 Claude Code 对话中直接调用 OpenSpace MCP 工具：

```
请调用 mcp__openspace__search_skills 搜索 "test"
```

如果返回 Skill 列表，说明 MCP 连接正常，安装成功。

---

## 7. 可选：本地仪表盘

查看 Skill 进化历史、谱系图和差异对比。

```bash
# 终端 1：启动后端 API
openspace-dashboard --port 7788

# 终端 2：启动前端开发服务器
cd OpenSpace/frontend
npm install        # 仅首次需要
npm run dev
```

浏览器打开前端地址即可查看仪表盘。

---

## 8. 可选：云端社区

1. 到 [open-space.cloud](https://open-space.cloud) 注册，获取 `OPENSPACE_API_KEY`
2. 将 API Key 添加到 `~/.claude.json` 的 `env` 块中
3. 解锁 `upload_skill`（上传 Skill 到云端）和云端 Skill 搜索

> 无 API Key 时，所有本地功能（任务执行、Skill 进化、本地搜索）正常工作。

---

## 9. 附录：配置文件速查

### 关键配置文件

| 文件 | 路径 | 用途 |
|------|------|------|
| **config_grounding.json** | `openspace/config/config_grounding.json` | Shell/Web/MCP/GUI 后端配置、工具搜索、Skill 引擎 |
| **config_agents.json** | `openspace/config/config_agents.json` | Agent 行为配置 |
| **config_security.json** | `openspace/config/config_security.json` | 安全策略 |
| **~/.claude.json** | `C:\Users\<用户名>\.claude.json` | Claude Code 全局配置（含 MCP Server 注册） |

### MCP Server 暴露的 4 个工具

| 工具 | 功能 | 无 API Key |
|------|------|-----------|
| `execute_task` | 多步 grounding agent 执行任务 | ✅ 可用 |
| `search_skills` | 本地 + 云端 Skill 搜索 | ✅ 仅本地 |
| `fix_skill` | 修复损坏的 SKILL.md | ✅ 可用 |
| `upload_skill` | 上传 Skill 到云端社区 | ❌ 需 API Key |

### Skill 自进化三种模式

| 模式 | 触发条件 | 行为 |
|------|----------|------|
| 🔧 **FIX** | Skill 出错/退化 | 就地修复同一 Skill |
| 🚀 **DERIVED** | 成功执行后分析 | 从父 Skill 创建增强版 |
| ✨ **CAPTURED** | 提取到新模式 | 创建全新 Skill |

---

## 问题速查表

| 症状 | 最可能原因 | 快速修复 |
|------|-----------|----------|
| `openspace-mcp --help` 无输出 | 正常行为（stdio MCP 服务器） | 检查退出码是否为 0 |
| MCP 工具调用失败 | 未在 `~/.claude.json` 注册 | 添加 `mcpServers.openspace` 配置 |
| Shell 命令全部 "unknown error" | `default_shell` 为 `/bin/bash` | 改为 `C:/Git/bin/bash.exe` |
| 配置修改未生效 | MCP Server 未重启 | 杀进程后重启 Claude Code 会话 |
| `upload_skill` 失败 | 缺少 `OPENSPACE_API_KEY` | 注册 open-space.cloud 获取 |
| Health check 无响应 | stdio 模式无 HTTP 端点 | 直接调用 MCP 工具验证 |
| `ModuleNotFoundError: websockets` | `pyproject.toml` 未声明依赖 | `pip install websockets` |
| 路径 JSON 转义异常 | 使用了反斜杠 `\\` | 统一使用正斜杠 `/` |

---

*本文档基于 OpenSpace v0.1.0 在 Windows 10 Pro + Claude Code 环境下的实际安装调试经历编写，所有问题均已验证解决。*
