# Warcraft 3 存档逆向工程知识库

## 概述

本文档记录 Warcraft 3 存档（.w3z）和录像（.w3g）文件格式逆向分析的完整过程、关键发现和可复用方法论。适用于后续类似的二进制格式逆向、游戏校验机制破解等任务。

---

## 零、参考资料与信息来源

### 0.1 关键认知：为什么是 game.dll？

在 Warcraft 3 逆向中，存档/录像的读写逻辑都在 **game.dll** 中，这是一个关键认知。理由如下：

1. **MPQ 读写在 Storm.dll，但存档是自定义格式**：
   - MPQ 归档（地图文件 .w3x、.w3m）的读写由 `Storm.dll` 负责（Ladislav Zezula 的 StormLib 逆向了这部分）
   - 但存档（.w3z）和录像（.w3g）不是 MPQ 格式，而是自定义的分块 zlib 压缩格式，由 `game.dll` 自己实现

2. **"Warcraft III recorded game" 字符串定位**：
   - 搜索 magic string `"Warcraft III recorded game\x1a\x00"` 在哪个 DLL 中被引用
   - 在 1.27a 版本中，这个字符串在 `game.dll` 的 0x6f9863d8 处
   - 引用该字符串的代码就是存档/录像的读写入口函数

3. **历史社区知识**：
   - w3g 录像格式的逆向研究（w3g.deepnode.de、w3gjs 等）早已确认录像解析逻辑在 game.dll 中
   - 存档（.w3z）与录像（.w3g）共享相同的分块压缩格式和 header 结构，因此也在 game.dll 中

### 0.2 重要开源参考项目

| 项目/资料 | 作者/来源 | 作用 |
|----------|-----------|------|
| **StormLib** | Ladislav Zezula | MPQ 格式的权威实现，参考了其压缩模块 SCompression.cpp 和 StormCommon.h |
| **w3g_format.txt** | w3g.deepnode.de | 经典的 w3g 录像格式文档，提供了 header 结构、块结构的基础认知 |
| **w3gjs** | 开源社区 | TypeScript 实现的 w3g 解析器，验证了编码字符串的掩码解码逻辑 |
| **w3g_scopatz.py** | scopatz | Python 版 w3g 解析器，参考了其 header 字段定义 |

### 0.3 为什么需要自己反汇编 game.dll？

虽然社区已有 w3g 录像格式的文档，但**存档校验和（块头 unknown 字段）的算法从未公开**。原因：

- w3g 是录像格式，用于观看回放，社区对录像的校验机制需求不高
- .w3z 存档的校验机制是暴雪的私有实现，用于防止作弊
- 公开文档只说了 "unknown"，没说算法
- 因此必须自己反汇编 game.dll 来破解

### 0.4 搜索路径总结

```
问题：修改地图后存档无法加载（"地图文件不一致"）
  ↓
初步探索：分析 .w3z 文件结构，找到 3 处疑似地图哈希的位置
  ↓
遇到瓶颈：块头 unknown 字段算法未知，暴力枚举几十种都不对
  ↓
转向反汇编：搜索 game.dll 中的 "recorded game" 字符串
  ↓
定位函数：从字符串引用点向上追溯，找到块读写函数和校验函数
  ↓
识别算法：发现 CRC32 表引用 + fold16 位操作模式
  ↓
确认算法：对比写入流程（最清晰）和读取校验流程，交叉验证
  ↓
验证：用多个存档的几十个块计算，全部匹配
```

---

## 一、文件格式结构

### 1.1 整体结构

```
┌──────────────────────────────────┐
│ Header (68 字节)                 │
│  - Magic: "Warcraft III          │
│    recorded game\x1a\x00"        │
│  - 文件大小、块数、CRC32 等       │
├──────────────────────────────────┤
│ 块 0                              │
│  ┌─ 块头 (8 字节) ─┐             │
│  │ comp_size  (2)  │             │
│  │ orig_size  (2)  │             │
│  │ unknown    (4)  │ ← 块校验和  │
│  └─────────────────┘             │
│  压缩数据 (zlib, level=1,        │
│            Z_SYNC_FLUSH)         │
├──────────────────────────────────┤
│ 块 1                              │
│ ... (同上)                        │
├──────────────────────────────────┤
│ 块 N (最后一块 orig_size < 65535) │
└──────────────────────────────────┘
```

### 1.2 Header 结构（68 字节）

| 偏移 | 大小 | 字段 | 说明 |
|------|------|------|------|
| 0x00 | 28 | Magic | "Warcraft III recorded game\x1a\x00" |
| 0x1C | 4 | header_size | header 总大小，固定为 68 (= 0x44) |
| 0x20 | 4 | file_size | 整个文件的总大小（字节） |
| 0x28 | 4 | decomp_size | 解压后总数据大小 |
| 0x2C | 4 | num_blocks | 数据块数量 |
| 0x40 | 4 | header_crc32 | 头部 CRC32（计算时此字段置0） |

### 1.3 块结构（每块）

| 偏移 | 大小 | 字段 | 说明 |
|------|------|------|------|
| 0 | 2 | comp_size | 压缩后大小（0 表示未压缩的全零块） |
| 2 | 2 | orig_size | 解压后大小（固定 65535，最后一块除外） |
| 4 | 4 | unknown | 块校验和（见算法章节） |
| 8 | comp_size | comp_data | zlib 压缩数据 |

- **每块最大解压大小**: 65535 字节（0xFFFF）
- **压缩方式**: zlib deflate, level=1, Z_SYNC_FLUSH
- **最后一块**: orig_size < 65535

---

## 二、块校验和算法（unknown 字段）

### 2.1 算法描述

块头第 4-7 字节（unknown 字段）是一个基于 CRC32 的折叠校验和，分两部分：

```
unknown 低16位 (偏移4-5) = fold16(CRC32(块头8字节, unknown=0))
unknown 高16位 (偏移6-7) = fold16(CRC32(压缩数据, comp_size))

fold16(x) = ((x >> 16) ^ x) & 0xFFFF
```

即：
```
unknown = fold16(crc_header) | (fold16(crc_data) << 16)
```

### 2.2 Python 实现

```python
import zlib

def fold16(x: int) -> int:
    """32位CRC折叠为16位: hi16 ^ lo16"""
    return ((x >> 16) ^ x) & 0xFFFF

def compute_block_checksum(block_header_8bytes: bytes, comp_data: bytes) -> int:
    """计算块校验和（unknown字段）"""
    # unknown 字段清零
    header_zeroed = bytearray(block_header_8bytes)
    header_zeroed[4:8] = b'\x00\x00\x00\x00'

    crc_header = zlib.crc32(bytes(header_zeroed)) & 0xFFFFFFFF
    crc_data = zlib.crc32(comp_data) & 0xFFFFFFFF

    return fold16(crc_header) | (fold16(crc_data) << 16)
```

### 2.3 破解过程回顾

1. **初始猜测阶段**：暴力测试了几十种算法（CRC32、CRC16、Adler32、各种字节序、高低位组合等），全部失败。
2. **转折点**：从反汇编 game.dll 入手，定位到块读取函数中的校验逻辑。
3. **关键线索**：校验函数内部调用了标准 CRC32 表（0xEDB88320 多项式），并且有 `shr 0x10 + xor` 的折叠操作。
4. **确认**：通过写入流程的反汇编（最清晰），确认了 low16 来自块头、high16 来自压缩数据。
5. **验证**：用多个存档的几十个块验证，全部匹配。

---

## 三、头部 CRC32 算法

### 3.1 算法描述

```
header_crc32 = CRC32(整个 68 字节 header, 其中 offset 0x40-0x43 置 0)
```

### 3.2 Python 实现

```python
def compute_header_crc(data: bytes) -> int:
    header = bytearray(data[:68])
    header[64:68] = b'\x00\x00\x00\x00'  # CRC32 字段清零
    return zlib.crc32(bytes(header)) & 0xFFFFFFFF
```

---

## 四、地图哈希校验机制

### 4.1 三处地图校验数据

修改地图后存档无法加载，是因为存档里存了 3 处地图校验数据，需要全部替换：

| 位置 | 大小 | 说明 |
|------|------|------|
| 编码字符串内（偏移+5） | 8 字节 | 地图校验码（编码字符串的游戏设置部分） |
| 编码字符串末尾 | 21 字节 | 1字节前缀 + 20字节 SHA1 |
| 明文区（约 0xf0 附近） | 28 字节 | 明文存储的校验数据（结构与编码字符串尾部对应） |

### 4.2 编码字符串格式

编码字符串是对「游戏设置 + 地图路径 + 创建者名称 + 尾部哈希」的掩码编码：

- **编码规则**：每 8 字节为一组，第 0 字节是掩码字节，后 7 字节是数据字节
- **掩码位含义**：如果掩码对应位为 0，表示该字节原值为 0xFF，编码时减 1 变成 0xFE；如果掩码位为 1，表示原值非 0xFF，直接存储
- **解码**：`if mask & (1 << (pos%8)) == 0: byte = (enc_byte - 1) & 0xFF else: byte = enc_byte`

### 4.3 编码/解码 Python 实现

```python
def decode_encoded(enc_data: bytes) -> bytes:
    encode_length = len(enc_data)
    decode_length = encode_length - (encode_length - 1) // 8 - 1
    decode_data = bytearray(decode_length)
    mask = 0
    decode_pos = 0
    encode_pos = 0
    while encode_pos < encode_length:
        if encode_pos % 8 == 0:
            mask = enc_data[encode_pos]
        else:
            if (mask & (1 << (encode_pos % 8))) == 0:
                decode_data[decode_pos] = (enc_data[encode_pos] - 1) & 0xFF
            else:
                decode_data[decode_pos] = enc_data[encode_pos]
            decode_pos += 1
        encode_pos += 1
    return bytes(decode_data)

def encode_encoded(dec_data: bytes, orig_enc: bytes = None) -> bytes:
    decode_length = len(dec_data)
    encode_length = decode_length + (decode_length - 1) // 7 + 1
    enc_data = bytearray(encode_length)
    use_orig_masks = orig_enc is not None and len(orig_enc) == encode_length
    mask = 0
    decode_pos = 0
    encode_pos = 0
    while encode_pos < encode_length:
        if encode_pos % 8 == 0:
            if use_orig_masks:
                mask = orig_enc[encode_pos]
            else:
                mask = 0x00
                for i in range(1, min(8, encode_length - encode_pos)):
                    if decode_pos + i - 1 < decode_length:
                        if dec_data[decode_pos + i - 1] == 0xFF:
                            mask |= (1 << i)
            enc_data[encode_pos] = mask
        else:
            idx = decode_pos
            if idx < decode_length:
                if (mask & (1 << (encode_pos % 8))) == 0:
                    enc_data[encode_pos] = (dec_data[idx] + 1) & 0xFF
                else:
                    enc_data[encode_pos] = dec_data[idx]
                decode_pos += 1
            else:
                enc_data[encode_pos] = 0xFF
        encode_pos += 1
    return bytes(enc_data)
```

### 4.4 替换流程（当地图文件名相同时）

1. 读取旧存档（提供游戏数据）和新存档（提供地图哈希）
2. 解压两个存档的块 0
3. 找到编码字符串位置
4. 解码 → 替换校验码(8字节)和尾部哈希(21字节) → 重新编码
5. 替换明文区 28 字节
6. 替换 0xea-0xec 的 3 字节（辅助校验数据）
7. 重新压缩块 0（zlib level=1, Z_SYNC_FLUSH）
8. 重新计算块 0 的 unknown 校验和
9. 更新文件大小、重新计算头部 CRC32

---

## 五、zlib 压缩参数

### 5.1 关键参数

| 参数 | 值 | 说明 |
|------|---|------|
| level | 1 | 最快压缩（不是默认的 6） |
| wbits | 15 | 标准 zlib 窗口大小 |
| flush | Z_SYNC_FLUSH | 每块结束时同步刷新（非常重要！） |

### 5.2 踩坑记录

- 一开始用默认 level=6 压缩，导致块大小与原版差异较大
- 更重要的是 `Z_SYNC_FLUSH`：如果用默认的 `Z_FINISH`，压缩流的结尾标志不同，解压校验可能失败
- 验证方法：压缩后立即解压，与原始数据逐字节比较，必须完全一致

```python
# 正确的压缩方式
compressor = zlib.compressobj(level=1, wbits=15)
comp_data = compressor.compress(raw_data)
comp_data += compressor.flush(zlib.Z_SYNC_FLUSH)
```

---

## 六、反汇编逆向方法论

### 6.1 工具选择

- **Capstone** (Python): 轻量级反汇编引擎，适合快速脚本化分析
- **x86 32位**: Warcraft 3 是 32 位程序，模式设为 `CS_ARCH_X86 + CS_MODE_32`

### 6.2 定位关键函数的思路

```
字符串搜索 → 交叉引用 → 调用链追踪 → 算法识别
```

1. **字符串搜索**：在 DLL 中搜索已知字符串（如 "Warcraft III recorded game"、"CORRUPT"）
2. **交叉引用**：找到引用该字符串的代码位置
3. **向上追溯**：从字符串引用点向上找函数入口
4. **识别关键操作**：
   - CRC32 表引用（标准多项式 0xEDB88320，前4个值为 00, 77073096, ee0e612c, 990951ba）
   - 表驱动循环（`movzx + xlat` 或数组索引模式）
   - 位操作指令（`shr`, `shl`, `xor`, `rol`, `ror`）
   - `cmp + jne` 校验比较点

### 6.3 常用汇编模式识别

| 模式 | 含义 |
|------|------|
| `xor reg, reg` | 寄存器清零 |
| `shr reg, 0x10` | 取高16位 |
| `movzx eax, word ptr [mem]` | 16位零扩展到32位 |
| `call [reg + offset]` | 虚函数调用（C++ 对象） |
| `lea edx, [eax + 8]` | 参数：长度 = 8（与当前值无关，就是传 8） |

### 6.4 函数大小估计

- 简单工具函数：~50-200 字节
- 中等业务函数：~200-1000 字节
- 核心流程函数：~1000-4000 字节
- 遇到 `ret` 后紧跟 `int3` (0xCC) 通常表示函数结束

---

## 七、关键函数地址（game.dll 1.27a 版本）

> 注意：这些地址是特定版本的，不同版本 game.dll 地址不同。

| 地址 | 函数名（推测） | 功能 |
|------|---------------|------|
| 0x6f887830 | CRC32 计算 | 标准 CRC32 表驱动实现 |
| 0x6f2f1fc0 | CRC32 包装器 | 封装 CRC32，处理参数 |
| 0x6f2f2600 | 块读取核心 | 读取并解压数据块 |
| 0x6f2f2a80 | 块写入核心 | 压缩并写入数据块（含校验和计算） |
| 0x6f2f22a0 | 读取校验流程 | 读取块并验证校验和 |
| 0x6f2f2c40 | 存档打开/创建 | 初始化存档结构，写入 header |
| 0x6f9630d8 | CRC32 表 | 标准 CRC32 查找表（256 * 4 字节） |

---

## 八、常见踩坑记录

### 8.1 subheader +0x20 不是地图哈希

- **坑**：一开始以为 header 偏移 0x20 处的 4 字节是地图哈希
- **真相**：那是**整个 header 的 CRC32 校验和**
- **教训**：替换后存档从列表中消失，说明那个字段是列表显示时就会校验的

### 8.2 块头 unknown 不是简单的 Adler32

- **坑**：zlib 压缩流末尾自带 Adler32，以为 unknown 就是它
- **真相**：unknown 是自定义的折叠 CRC32
- **教训**：不要假设，一定要反汇编确认

### 8.3 压缩参数必须匹配

- **坑**：用默认 zlib 压缩参数（level=6, Z_FINISH）
- **真相**：魔兽用 level=1 + Z_SYNC_FLUSH
- **后果**：虽然能解压，但块大小和校验和都不对

### 8.4 地图文件名不同导致偏移错位

- **坑**：两个存档地图文件名不同时，编码字符串长度不同，后面的明文区等偏移全变了
- **解决**：优先用同名地图做对比实验；如果必须不同名，需要按字段替换而非按偏移替换

### 8.5 编码字符串的掩码不能忽略

- **坑**：直接修改编码后字节，不重新计算掩码
- **真相**：掩码字节决定了数据字节的解释方式
- **解决**：解码 → 修改 → 重新编码（尽量沿用原掩码）

---

## 九、验证检查清单

修改存档后，按以下顺序验证：

- [ ] **文件大小**: `len(file) == header.file_size`
- [ ] **头部 CRC32**: `compute_header_crc(data) == header.header_crc`
- [ ] **块数一致**: 实际块数 == header.num_blocks
- [ ] **每块 unknown**: 对所有块，`compute_block_checksum(header, data) == block.unknown`
- [ ] **解压验证**: 每块压缩数据解压后与原始数据逐字节一致
- [ ] **地图哈希**: 编码字符串解码后的校验码与目标版本一致
- [ ] **实际加载**: 在游戏中能正常显示预览图并进入游戏

---

## 十、工具与脚本

### 核心工具

- **w3z_maphash.py** - 三合一主工具（inspect / replace / verify）
  - `inspect <path>`: 查看存档信息、地图哈希
  - `replace <old_save> <new_save> <out>`: 替换地图哈希
  - `verify <path>`: 验证存档完整性

### 辅助工具

- **w3z_tool.py** - 基础存档工具（unpack / pack / scan-rawcodes）
- **mpq_parser_fixed.py** - MPQ 归档解析器
- **analyze_w3z_full.py** - 全量解压分析

### 反汇编工具链

- Capstone (Python `capstone` 包)
- 十六进制查看器（可选）

---

## 十一、版本兼容性说明

| 版本 | 特点 |
|------|------|
| 1.20-1.27 | 32位，game.dll 内联 CRC32 表 |
| 1.28+ | 可能有变化，未验证 |
| 重制版 | 64位，完全不同，未验证 |

本知识库的所有结论基于 **1.27a 版本** 的 game.dll。

---

## 十二、逆向工程通用原则

1. **先验证假设，再写代码**：猜测了算法后，先用已知数据验证，不要上来就写完整工具
2. **暴力枚举是最后的手段**：先从字符串、导入表、已知算法特征入手，比瞎猜效率高得多
3. **反汇编是金标准**：当暴力枚举失败时，直接反汇编目标函数是最快的路径
4. **写入流程比读取流程更容易分析**：写入时数据流向清晰，赋值操作一眼就能看懂
5. **每一步都要验证**：解压验证、校验和验证、对比验证——验证越多，bug越少
6. **开源社区优先**：遇到格式问题先搜 GitHub，很多时候已经有现成的解析器了
