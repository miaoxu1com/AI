---
name: skill-writing-conventions
description: Use when writing or refactoring SKILL.md files.
version: 1.0.0
---

# Skill 编写规范

编写或重构 SKILL.md 时遵循以下规则。

## 结构与拆分

| 规则 | 说明 |
|------|------|
| 主文件 ≤ 150 行 | 超出则拆分到 references/*.md |
| 拆分最多两层 | SKILL.md → references/*.md，不再往下拆 |
| 拆分保持子步骤完整 | 不过度拆分，每个子文件是一个完整子流程 |
| 子步骤按顺序编排 | 主文件按执行顺序列出步骤，引用子文件补充细节 |

## 写作风格

| 规则 | 说明 |
|------|------|
| 表格和流程图优先 | 用表格和流程图代替大篇幅文字描述 |
| 简短精炼 | 每句话意义明确，禁止冗余和模糊 |
| 不重复代码/配置已有的逻辑 | 代码和配置文件已实现的细节不写进 SKILL.md，用一行指引到对应文件 |
