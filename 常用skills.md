### 环境配置
- CLAUDE_CODE_GIT_BASH_PATH=C:\Git\bin\bash.exe
- CLAUDE_CODE_USE_POWERSHELL_TOOL=1
- "hasCompletedOnboarding": true

**注意**：

#### Claude Mem 改为api-auth
- ~/.claude-mem/settings.json
  
```shell
"CLAUDE_MEM_PROVIDER": "claude",
"CLAUDE_MEM_MODEL": "deepseek-v4-flash",
"CLAUDE_MEM_CLAUDE_AUTH_METHOD": "api-key",
"ANTHROPIC_AUTH_TOKEN": "sk-你的DeepSeek-API-Key",
"ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic"
```
- .claude-mem/.env
  
```shell
# ~/.claude-mem/.env
ANTHROPIC_AUTH_TOKEN=sk-你的DeepSeek-API-Key
ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
```
#### 重启 worker

```shell
# 1. 找到并杀掉旧 worker
Get-Content ~/.claude-mem/worker.pid  # 获取 PID
Stop-Process -Id <PID> -Force

# 2. 清理 PID 文件（可选，worker 会自动处理 stale PID）
Remove-Item ~/.claude-mem/worker.pid

# 3. 重新触发 Claude Code 会话——worker 会自动启动
```

#### 验证修复

```shell
# 检查日志中的 SDK 返回长度——应该远超 33 chars
Select-String -Path ~/.claude-mem/logs/claude-mem-*.log -Pattern "Response received"

# 修复前：全部是 "(33 chars)"
# 修复后：出现 "(750 chars)"、"(1203 chars)"、"(2687 chars)" 等

# 打开 dashboard 确认 observation 已落库
Start-Process "http://127.0.0.1:37777"
```

- https://blog.csdn.net/ZxqSoftWare/article/details/161293220


### SKills仓库路径

- https://github.com/charon-fan/agent-playbook
- https://skillsmp.com/skills
- https://www.skills.sh
- https://lobehub.com/skills
- https://cn.clawhub-mirror.com
- https://agentskill.sh/
- https://skillhub.cn/

#### Plugins
##### 安装
- npx claude-mem install
  - **注意**：npx安装的插件无法在/plugin中管理
- /plugin marketplace add thedotmack/claude-mem
  - /plugin install claude-mem
- scoop install bun
- 启动claude mem worker
  - cd ~/.claude/plugins/marketplaces/thedotmack
  - npm run worker:restart
##### 卸载
- npx claude-mem uninstall -g
- /plugin uninstall claude-mem

##### 插件缓存清理
- .claude\plugins\cache
#### claw下载解压直接放入claude skill可以生效，实际测试skill-vetter

#### SKill参数代表仓库下skills目录

- skill 目录 用户目录下的.agents/skills
- npx skills add https://github.com/anthropics/skills --skill skill-creator
- npx skills add https://github.com/vercel-labs/skills --skill find-skills
- npx skills add https://github.com/Yeachan-Heo/oh-my-claudecode --skill self-improve
- npx skills add mattpocock/skills

#### Skills 的加载机制可能有两个来源：
  - 1. .skill-lock.json 中注册的 skills（通过 npx skills add 安装的）
  - 2. .agent存放第三方安装的skills
  - 3. .claude/skills/ 目录下的 skills（用户自定义）
