---
name: "jass-map-modifier"
description: "修改 Warcraft 3 地图 war3map.j 脚本，解锁商城物品、英雄皮肤、积分资源、隐藏彩蛋等。在用户要求修改魔兽地图 JASS 脚本、解锁付费内容、调整游戏数值时调用。"
---

# JASS 地图修改器

本 Skill 用于修改 Warcraft 3 地图的 war3map.j 脚本文件，解锁各种付费内容和隐藏功能。

## 一、JASS 语法硬约束（违反会导致游戏无法启动）

### 1. native 和 function 的顺序
- **所有 `native` 声明必须在 `function` 定义之前**
- 禁止在 `native` 声明中间插入 `function` 定义
- 自定义 `function` 必须插入在最后一个 `native` 声明之后、第一个 `function` 定义之前

### 2. 禁止重复定义
- **禁止同时存在同名的 native 和 function（会导致游戏无法启动）**
- 覆盖 native 的正确做法：删除 native 声明，用 function 替代

### 3. 修改前的原则
- 修改代码前必须先充分探索和理解代码，禁止猜测、编造
- 所有修改必须建立在充分了解代码逻辑的基础上
- 不确定的地方必须先确认，禁止凭猜测修改

## 二、常用修改方法

### 方法一：覆盖 native 函数（解锁平台限制）

**适用场景**：解锁商城物品、地图等级等平台API限制

**步骤**：
1. 找到 native 函数声明位置
2. 删除 native 声明
3. 在最后一个 native 之后、第一个 function 之前插入同名 function

**示例 - 解锁商城物品**：
```jass
// 删除原 native 声明
// native DzAPI_Map_HasMallItem takes player whichPlayer, string key returns boolean

// 在 native 区末尾插入
function DzAPI_Map_HasMallItem takes player whichPlayer, string key returns boolean
    return true
endfunction
```

### 方法二：修改已有 function 的返回值

**适用场景**：修改 KK API 等已经是 function 的平台函数

**步骤**：
1. 找到 function 定义位置
2. 直接修改 return 语句

**示例 - 解锁消费等级**：
```jass
// 修改前
function KKApiConsumeLevel takes player whichPlayer,integer mapId returns integer
    return RequestExtraIntegerData(115, whichPlayer, null, null, false, mapId, 0, 0)
endfunction

// 修改后
function KKApiConsumeLevel takes player whichPlayer,integer mapId returns integer
    return 100
endfunction
```

### 方法三：变量初始化偏移量

**适用场景**：增加初始资源（积分、碎片等）

**步骤**：
1. 找到变量从服务器读取后的赋值语句
2. 在赋值语句后立即添加偏移量

**示例 - 初始化通关积分**：
```jass
set udg_TGJF[ydul_i]=DzAPI_Map_GetStoredInteger(... , "GCTGJF")
set udg_TGJF[ydul_i]=( udg_TGJF[ydul_i] + 10000 )  // 添加这一行
```

### 方法四：修改初始显示状态

**适用场景**：解锁隐藏NPC、彩蛋商人等

**步骤**：
1. 找到 `ShowUnit` 初始设置
2. 将 `false` 改为 `true`

**示例 - 解锁彩蛋商人**：
```jass
// 修改前
call ShowUnit(gg_unit_H003_0036, false)

// 修改后
call ShowUnit(gg_unit_H003_0036, true)
```

## 三、平台 API 分类与修改策略

### DzAPI 系列（魔兽官方对战平台）

| API 函数 | 功能 | 修改策略 |
|---------|------|----------|
| DzAPI_Map_HasMallItem | 检查商城物品 | 改为返回 true |
| DzAPI_Map_GetMapLevel | 获取地图等级 | 改为返回 100 |
| DzAPI_Map_GetStoredInteger | 读取存储整数 | 读取后加偏移量 |
| DzAPI_Map_StoreInteger | 存储整数 | 一般不需要改 |

### KKApi 系列（KK 对战平台）

| API 函数 | 功能 | 修改策略 |
|---------|------|----------|
| KKApiConsumeLevel | 消费等级 | 改为返回 100 |
| KKApiIsAchievementCompleted | 成就是否完成 | 改为返回 true |
| KKApiGetMapLevel | 地图等级 | 改为返回高等级 |

## 四、常见内容解锁对应关系

### 英雄皮肤
- 大多数皮肤：通过 `DzAPI_Map_HasMallItem` 检查（商城购买）
- 彩蛋英雄皮肤（如豚豚精灵传说）：通过 `KKApiConsumeLevel` 检查（消费等级）
- 成就称号：通过 `KKApiIsAchievementCompleted` 检查

### 英雄解锁
- 氪金英雄：`DzAPI_Map_HasMallItem` + 科技ID（如 R001, R002）
- 等级解锁英雄：`DzAPI_Map_GetMapLevel` + 等级阈值
- 彩蛋英雄：通过隐藏NPC商店购买，需先解锁NPC显示

### 积分/资源
- 通关积分：`udg_TGJF`，从服务器读取后加偏移
- 观测积分：`udg_TGJF1` = `udg_TGJF` + 25 × 工厂进阶次数

## 五、修改前检查清单

1. ✅ 确认要修改的函数是 native 还是 function
2. ✅ 如果是 native，先找到声明位置，准备删除并替换
3. ✅ 确认替换的 function 插入位置（最后一个 native 之后）
4. ✅ 检查是否有同名函数重复定义
5. ✅ 理解修改后的影响范围（是否会影响其他系统）
6. ✅ 确认没有违反 JASS 语法规则

## 六、验证方法

1. 搜索修改的函数名，确认只有一个定义
2. 检查 native 区是否没有 function 定义
3. 确认 function 定义都在 native 区之后
4. 测试游戏是否能正常启动

## 七、属性奖励验证（解锁后必做）

**原则：解锁内容若附带属性奖励，修改完成后必须逐一验证属性加成是否实际生效。**

### 验证步骤

1. **搜索所有调用点**：对被覆盖的函数（如 `DzAPI_Map_HasMallItem`、`DzAPI_Map_GetMapLevel`、`RequestExtraIntegerData`），全局搜索所有调用位置
2. **追踪属性加成分支**：对每个调用点，检查 `if` 条件成立后执行的代码块，关注以下属性变量：
   - 属性倍率类：`udg_BFLL`/`udg_BFMJ`/`udg_BFZL`（力量/敏捷/智力倍率）
   - 攻击加成类：`udg_GJDJ`/`udg_GJL`（攻击等级/攻击力）
   - 生命加成类：`udg_SM`/`udg_ZSM`（生命倍率/生命附加值）
   - 资源加成类：`udg_K_XY`/`udg_K_JB`/`udg_K_JY`（幸运/金币/经验倍率）
   - 科技研发类：`SetPlayerTechResearchedSwap` 调用
3. **确认条件链完整性**：若调用点存在多重条件（如 `HasMallItem AND RequestExtraIntegerData(41,...)>=N`），确认所有子条件均能通过
4. **确认变量赋值时机**：属性加成代码所在的触发器是否会在游戏初始化时执行（如定时器触发 `TimerEventSingle`），避免加成代码从未运行
5. **检查原代码 Bug**：注意原代码中可能存在的变量误用（如在定时器触发中使用 `GetTriggerPlayer()` 返回 null），此类 Bug 非修改引入但需如实告知用户

### 验证结果输出格式

对每类解锁内容，以表格形式列出：
- 解锁项名称
- 对应属性变量及加成值
- 生效状态（✅ 正常 / ⚠️ 原代码Bug / ❌ 未生效）
- 若未生效需说明原因和修复建议
