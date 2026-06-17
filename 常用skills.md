### SKills仓库路径

- https://github.com/charon-fan/agent-playbook
- https://skillsmp.com/skills
- https://www.skills.sh
- https://lobehub.com/skills
- https://cn.clawhub-mirror.com
- https://agentskill.sh/
- https://skillhub.cn/

#### Plugins
- npx claude-mem install /plugin marketplace add thedotmack/claude-mem /plugin install claude-mem
- 
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
