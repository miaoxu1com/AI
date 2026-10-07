# 项目规则 - 魔兽3地图修改与存档逆向

## 项目概述

本项目用于魔兽争霸3地图的修改、调试和存档逆向分析。主要涉及：
- JASS 脚本（war3map.j）修改
- `.w3z` 存档文件逆向与修复
- MPQ 归档操作
- 付费内容解锁、作弊功能添加

## 核心约束

### JASS 语法规则（必须严格遵守）

1. **native 声明必须在 function 定义之前**
   - 所有 native 声明必须在文件的前部
   - 禁止在 native 声明中间插入 function 定义

2. **自定义 function 的插入位置**
   - 自定义 function 必须插入在最后一个 native 声明之后、第一个 function 定义之前

3. **禁止同名的 native 和 function**
   - 同时存在同名的 native 和 function 会导致游戏无法启动
   - 覆盖 native 的正确做法：删除 native 声明，用 function 替代

4. **1.27 版本兼容性**
   - 1.27 引擎不支持扩展键（如 PGUP、PGDN），仅支持 4 个方向键（LEFT/RIGHT/UP/DOWN）
   - 1.27 引擎缺少 `BlzGetUnitBaseDamage` 等 native，需要用 stub 函数替代

### 修改代码前的流程

1. **先充分探索和理解代码，禁止猜测、编造**
2. **修改前必须先搜索相关代码，理解其含义和上下文**
3. **所有修改必须建立在充分了解代码逻辑的基础上**
4. **不确定的地方必须先确认，禁止凭猜测修改**

### 中间产物清理

- 任务过程中产生的临时文件、测试文件、解压产物等中间物，在完成最终任务后必须清理
- 禁止在工作目录中残留垃圾文件
- 测试用的临时文件统一放在 `test/` 目录下，任务完成后删除
- **只清理自己产生的文件**，绝对不要删除用户已有的文件，防止误删除
- 清理前必须确认文件是本次任务中创建的，不确定的文件保留不动

## 常用工作流

### 修改 war3map.j

1. 先搜索相关代码，理解上下文
2. 使用 Edit 工具进行精确修改
3. 遵循 JASS 语法规则

### 存档分析与修改

1. 使用 `war3-save-reverse` skill 中的 `w3z_tool.py`
2. 命令：`python .trae/skills/war3-save-reverse/scripts/w3z_tool.py inspect <file>`
3. 支持 inspect / unpack / pack / scan-rawcodes 四种模式

### 数值调整原则

- 调整数值时，如果过高导致意外 bug，优先恢复原始增量
- 逐步调整，每次只改一个变量

## 相关工具与路径

### 地图目录
- 地图文件：`g:\games\Warcraft3\Maps\Download\`
- 存档目录：`G:\games\Warcraft3\Save\`
- 魔兽根目录：`G:\games\Warcraft3\`

### 技能（Skills）
- `war3-save-reverse` - 存档逆向分析工具
- `jass-map-modifier` - JASS 地图修改工具

### 重要文件
- `dz_w3_plugin.ini` - 平台存档数据（DzAPI 模拟）
- `dz_w3_plugin.dll` - DzAPI 平台模拟插件
- `bin/modules/maphash.dll` - 地图哈希计算模块

## 存档校验知识

- 魔兽3使用基于 MPQ 内容的特殊哈希算法（非简单 MD5/CRC32）
- `.w3z` 存档结构：8 字节块头部（u16 comp_size + u16 orig_size + u32 unknown）+ zlib 数据
- 录像（.w3g）块大小：8192 字节；存档（.w3z）块大小：65535 字节
- 修改地图后哈希会变化，导致原有存档无法加载

## 开源社区优先原则

遇到技术问题时，优先在 GitHub 等开源社区搜索已有解决方案，避免从零开始重复造轮子。社区中积累了大量经过验证的高质量代码、格式文档、解析器和工具，应站在巨人肩上前进。

**执行策略：**
- 动手实现前，先用 WebSearch 搜索 GitHub 上的相关开源项目
- 优先查找格式规范文档、成熟解析器、逆向工程工具
- 借鉴开源代码的思路、算法、数据结构，而非重新发明
- 在已有方案基础上适配和优化

## 沟通语言

- 默认使用中文交流
- 代码和技术术语保持英文原文
