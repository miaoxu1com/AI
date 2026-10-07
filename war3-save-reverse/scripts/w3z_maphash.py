#!/usr/bin/env python3
"""
魔兽3存档地图哈希提取与替换工具

用法:
  python w3z_maphash.py extract <save.w3z>           # 提取地图哈希
  python w3z_maphash.py replace <old.w3z> <new.w3z>  # 用new的哈希替换old的哈希
  python w3z_maphash.py info <save.w3z>              # 显示存档信息
  python w3z_maphash.py verify <save.w3z>            # 验证存档完整性

原理:
  魔兽3存档(.w3z)的解压数据中，地图路径和校验信息存储在编码字符串中。
  编码字符串使用掩码编码（每8字节一组，第0字节为掩码）。
  解码后，前13字节是游戏设置，其中后8字节（offset 5-12）是地图校验码。
  创建者名称之后还有21字节的尾部数据（1字节0x00 + 20字节SHA1）。

  地图校验数据共3处需要替换：
  1. 编码字符串内：8字节校验码(offset 5-12) + 21字节尾部哈希
  2. 明文区28字节：第一块解压数据 offset 0xf0-0x10b
     [前4字节未知] + [校验码后4字节] + [20字节SHA1]
  3. 0xea-0xec 的3字节：位于明文区之前，随地图版本变化

  替换后必须重新计算两个校验和：
  - 块0 unknown 字段（块头 offset +4，4字节）
    算法: unknown = fold16(CRC32(块头8字节,unknown=0)) | (fold16(CRC32(压缩数据)) << 16)
    其中 fold16(x) = ((x >> 16) ^ x) & 0xFFFF
  - 头部 CRC32（offset 0x40，4字节）：对68字节header计算，CRC32位置置0
  - 文件大小（offset 0x20，4字节）：更新为实际文件大小

  压缩参数: level=1 + Z_SYNC_FLUSH (匹配魔兽3的zlib参数)
"""
import struct
import zlib
import pathlib
import sys

SIG = b"Warcraft III recorded game\x1a\x00"
HEADER_SIZE_OFFSET = 28      # uint32, header大小 (=68)
FILE_SIZE_OFFSET = 0x20      # uint32, 文件总大小 (subheader +0x00)
NUM_BLOCKS_OFFSET = 0x2c     # uint32, 块数 (subheader +0x0c)
HEADER_CRC_OFFSET = 0x40     # uint32, 头部CRC32 (subheader +0x20)
HEADER_TOTAL = 68            # header总大小
BLOCK_ORIG_SIZE = 65535       # 每块解压大小（除最后一块）


def fold16(x: int) -> int:
    """将32位CRC折叠为16位: (x>>16) ^ x"""
    return ((x >> 16) ^ x) & 0xFFFF


def compute_block_checksum(block_header_8bytes: bytes, comp_data: bytes) -> int:
    """
    计算块校验和（块头 unknown 字段）
    块头结构: comp_size(2) + orig_size(2) + unknown(4)
    算法: unknown = fold16(CRC32(块头,unknown=0)) | (fold16(CRC32(压缩数据)) << 16)
    """
    header_zeroed = bytearray(block_header_8bytes)
    header_zeroed[4:8] = b'\x00\x00\x00\x00'
    crc_header = zlib.crc32(bytes(header_zeroed)) & 0xFFFFFFFF
    crc_data = zlib.crc32(comp_data) & 0xFFFFFFFF
    return fold16(crc_header) | (fold16(crc_data) << 16)


def compute_header_crc(data: bytes) -> int:
    """计算头部 CRC32: 整个68字节header, CRC32位置(0x40-0x43)置0"""
    header = bytearray(data[:HEADER_TOTAL])
    header[64:68] = b'\x00\x00\x00\x00'
    return zlib.crc32(bytes(header)) & 0xFFFFFFFF

def unpack_first_block(w3z_path: pathlib.Path) -> bytes:
    """解压存档的第一块数据"""
    data = w3z_path.read_bytes()
    header_size = struct.unpack_from('<I', data, len(SIG))[0]
    pos = header_size
    if pos + 8 > len(data):
        raise ValueError("Invalid w3z file: no data blocks")
    
    comp_size, orig_size = struct.unpack_from('<HH', data, pos)
    comp_data = data[pos+8:pos+8+comp_size]
    
    if comp_size == 0:
        return b'\x00' * orig_size
    
    decompressor = zlib.decompressobj(wbits=15)
    raw = decompressor.decompress(comp_data)[:orig_size]
    return raw

def find_encoded_string(raw: bytes) -> tuple:
    """
    在解压数据中找到编码字符串的位置
    返回: (起始位置, 结束位置, 编码数据)
    """
    # 找到 Maps\ 路径
    maps_pos = raw.find(b'Maps\\')
    if maps_pos == -1:
        raise ValueError("Map path not found in save data")
    
    # 跳过地图路径
    path_end = raw.find(b'\x00', maps_pos)
    pos = path_end + 1
    
    # 跳过 null 字节
    while pos < len(raw) and raw[pos] == 0:
        pos += 1
    
    # 跳过游戏名称（UTF-8，null结尾）
    while pos < len(raw) and raw[pos] != 0:
        pos += 1
    pos += 1
    
    # 跳过 null 字节
    while pos < len(raw) and raw[pos] == 0:
        pos += 1
    
    # 现在是编码字符串的起始
    enc_start = pos
    enc_end = pos
    while enc_end < len(raw) and raw[enc_end] != 0:
        enc_end += 1
    
    return enc_start, enc_end, raw[enc_start:enc_end]

def decode_encoded_string(enc_data: bytes) -> bytes:
    """解码 w3g 编码字符串"""
    encode_length = len(enc_data)
    if encode_length == 0:
        return b''
    
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

def encode_encoded_string(dec_data: bytes, orig_enc: bytes = None) -> bytes:
    """
    重新编码 w3g 编码字符串
    如果提供 orig_enc，则保留原始掩码字节，只替换数据字节
    编码规则: 每 8 字节一组，第 0 字节是掩码，后 7 字节是数据
    """
    decode_length = len(dec_data)
    if decode_length == 0:
        return b''
    
    # 每组 1 掩码 + 7 数据 = 8 编码字节 → 7 解码字节
    encode_length = decode_length + (decode_length - 1) // 7 + 1
    enc_data = bytearray(encode_length)
    
    # 如果有原始编码数据，复用其掩码字节
    use_orig_masks = orig_enc is not None and len(orig_enc) == encode_length
    
    mask = 0
    decode_pos = 0
    encode_pos = 0
    
    while encode_pos < encode_length:
        if encode_pos % 8 == 0:
            if use_orig_masks:
                # 复用原始掩码
                mask = orig_enc[encode_pos]
            else:
                # 计算掩码：默认用 bit=0（shift），
                # 但如果 d+1 会产生 0x00（即 d=0xFF），则必须用 bit=1（as-is）
                mask = 0x00
                for i in range(1, min(8, encode_length - encode_pos)):
                    if decode_pos + i - 1 < decode_length:
                        d = dec_data[decode_pos + i - 1]
                        if d == 0xFF:
                            mask |= (1 << i)  # 必须用 as-is，否则 d+1=0x00 会截断
            enc_data[encode_pos] = mask
        else:
            idx = decode_pos
            if idx < decode_length:
                if (mask & (1 << (encode_pos % 8))) == 0:
                    # bit=0: 编码 = d + 1
                    enc_data[encode_pos] = (dec_data[idx] + 1) & 0xFF
                else:
                    # bit=1: 编码 = d (as-is)
                    enc_data[encode_pos] = dec_data[idx]
                decode_pos += 1
            else:
                enc_data[encode_pos] = 0xFF  # 填充
        encode_pos += 1
    
    return bytes(enc_data)

def extract_map_info(raw: bytes) -> dict:
    """从解压数据中提取地图信息"""
    enc_start, enc_end, enc_data = find_encoded_string(raw)
    dec_data = decode_encoded_string(enc_data)
    
    # 前13字节是游戏设置
    game_settings = dec_data[:13]
    map_checksum_8 = game_settings[5:13]  # 8字节地图校验码
    
    # 地图路径
    pos = 13
    while pos < len(dec_data) and dec_data[pos] != 0:
        pos += 1
    map_path = dec_data[13:pos].decode('utf-8', errors='replace')
    pos += 1
    
    # 创建者名称
    creator_start = pos
    while pos < len(dec_data) and dec_data[pos] != 0:
        pos += 1
    creator = dec_data[creator_start:pos].decode('utf-8', errors='replace')
    pos += 1
    
    # 尾部数据（可能是SHA-1哈希）
    trailing = dec_data[pos:]
    
    return {
        'enc_start': enc_start,
        'enc_end': enc_end,
        'enc_data': enc_data,
        'dec_data': dec_data,
        'game_settings': game_settings,
        'map_checksum_8': map_checksum_8,
        'map_path': map_path,
        'creator': creator,
        'trailing_hash': trailing,
    }

def cmd_info(w3z_path: pathlib.Path):
    """显示存档信息"""
    raw = unpack_first_block(w3z_path)
    info = extract_map_info(raw)
    
    print(f"存档文件: {w3z_path}")
    print(f"地图路径: {info['map_path']}")
    print(f"创建者:   {info['creator']}")
    print(f"游戏设置: {info['game_settings'].hex()}")
    print(f"校验码(8字节): {info['map_checksum_8'].hex()}")
    print(f"尾部哈希({len(info['trailing_hash'])}字节): {info['trailing_hash'].hex()}")
    
    # 也显示 subheader
    data = w3z_path.read_bytes()[:128]
    header_size = struct.unpack_from('<I', data, len(SIG))[0]
    subheader = data[len(SIG)+4:len(SIG)+header_size]
    print(f"\n外头部 subheader ({len(subheader)} bytes):")
    for i in range(0, len(subheader), 4):
        if i + 4 <= len(subheader):
            v = struct.unpack_from('<I', subheader, i)[0]
            print(f"  +0x{i:02x}: 0x{v:08x}")

def cmd_extract(w3z_path: pathlib.Path):
    """提取地图哈希"""
    raw = unpack_first_block(w3z_path)
    info = extract_map_info(raw)
    
    print(f"地图路径: {info['map_path']}")
    print(f"校验码(8字节): {info['map_checksum_8'].hex()}")
    print(f"尾部哈希({len(info['trailing_hash'])}字节): {info['trailing_hash'].hex()}")
    
    # 保存到文件
    hash_file = w3z_path.with_suffix('.maphash')
    with open(hash_file, 'wb') as f:
        f.write(info['map_checksum_8'])
        f.write(info['trailing_hash'])
    print(f"\n哈希已保存到: {hash_file}")

def _unpack_block0_with_meta(data: bytes):
    """解压块0，返回 (raw, unknown, comp_size, orig_size, block_pos)"""
    hs = struct.unpack_from('<I', data, HEADER_SIZE_OFFSET)[0]
    comp_size, orig_size, unknown = struct.unpack_from('<HHI', data, hs)
    comp_data = data[hs + 8:hs + 8 + comp_size]
    if comp_size == 0:
        raw = b'\x00' * orig_size
    else:
        decompressor = zlib.decompressobj(wbits=15)
        raw = decompressor.decompress(comp_data)[:orig_size]
    return raw, unknown, comp_size, orig_size, hs


def cmd_replace(old_path: pathlib.Path, new_path: pathlib.Path, out_path: pathlib.Path = None, level: int = 1):
    """
    用 new 存档的地图哈希替换 old 存档的地图哈希
    生成 old_patched.w3z（或指定 out_path）

    替换3处地图校验数据：
    1. 编码字符串内：8字节校验码 + 21字节尾部哈希
    2. 明文区28字节 (offset 0xf0-0x10b)
    3. 0xea-0xec 的3字节

    重新计算2处校验和：
    - 块0 unknown（块头 offset +4）
    - 头部 CRC32 (offset 0x40)
    同时更新文件大小 (offset 0x20)
    """
    old_data = bytearray(old_path.read_bytes())
    new_data = new_path.read_bytes()

    old_raw, old_unk, old_comp, old_orig, old_block_pos = _unpack_block0_with_meta(bytes(old_data))
    new_raw, new_unk, new_comp, new_orig, new_block_pos = _unpack_block0_with_meta(new_data)

    print(f"原版块0: comp_size={old_comp}, orig_size={old_orig}, unknown=0x{old_unk:08x}")
    print(f"修改版块0: comp_size={new_comp}, orig_size={new_orig}, unknown=0x{new_unk:08x}")

    # 验证原版块校验和算法
    old_comp_data = bytes(old_data[old_block_pos + 8:old_block_pos + 8 + old_comp])
    old_block_header = struct.pack('<HHI', old_comp, old_orig, old_unk)
    calc_unk = compute_block_checksum(old_block_header, old_comp_data)
    algo_ok = calc_unk == old_unk
    print(f"\n验证原版块校验和算法: 文件=0x{old_unk:08x}, 计算=0x{calc_unk:08x}, "
          f"{'✓' if algo_ok else '✗'}")
    if not algo_ok:
        print("警告: 块校验和算法验证失败，补丁可能无法加载！")

    # 找编码字符串
    old_enc_start, old_enc_end, old_enc = find_encoded_string(old_raw)
    _, _, new_enc = find_encoded_string(new_raw)
    old_dec = decode_encoded_string(old_enc)
    new_dec = decode_encoded_string(new_enc)

    print(f"\n编码字符串: 旧={len(old_enc)}字节, 新={len(new_enc)}字节")
    print(f"  解码: 旧={len(old_dec)}字节, 新={len(new_dec)}字节")

    # 替换校验码（offset 5-12, 8字节）和尾部哈希（最后21字节）
    if len(old_dec) != len(new_dec):
        print(f"警告: 解码数据长度不同 ({len(old_dec)} vs {len(new_dec)})")
        return False

    new_dec_full = bytearray(old_dec)
    new_dec_full[5:13] = new_dec[5:13]  # 8字节校验码
    old_trailing_start = len(old_dec) - 21
    new_dec_full[old_trailing_start:] = new_dec[len(new_dec) - 21:]  # 21字节尾部

    # 重新编码（复用原始掩码字节）
    new_enc_data = encode_encoded_string(bytes(new_dec_full), old_enc)

    # 验证编码
    verify_dec = decode_encoded_string(new_enc_data)
    if verify_dec != bytes(new_dec_full):
        print("错误: 重新编码后解码验证失败！")
        diff_count = 0
        for i in range(min(len(verify_dec), len(new_dec_full))):
            if verify_dec[i] != new_dec_full[i]:
                if diff_count < 20:
                    print(f"  差异 offset {i}: 期望={new_dec_full[i]:02x} 实际={verify_dec[i]:02x}")
                diff_count += 1
        return False
    print("编码字符串: 验证通过 ✓")

    # 构建新的块0解压数据：替换3处地图校验
    new_block_raw = bytearray(old_raw)
    new_block_raw[old_enc_start:old_enc_end] = new_enc_data   # 1. 编码字符串
    new_block_raw[0xf0:0xf0 + 28] = new_raw[0xf0:0xf0 + 28]  # 2. 明文区28字节
    new_block_raw[0xea:0xed] = new_raw[0xea:0xed]             # 3. 0xea-0xec 3字节
    print("已替换: 编码字符串 + 明文区28字节 + 0xea-0xec")

    # 重新压缩（level=1 + Z_SYNC_FLUSH 匹配魔兽3参数）
    compressor = zlib.compressobj(level=level, wbits=15)
    new_comp_data = compressor.compress(bytes(new_block_raw))
    new_comp_data += compressor.flush(zlib.Z_SYNC_FLUSH)
    new_comp_size = len(new_comp_data)
    print(f"\n第一块压缩: {old_comp} -> {new_comp_size} (level={level}, Z_SYNC_FLUSH)")

    # 验证解压
    d = zlib.decompressobj(wbits=15)
    verify_decomp = d.decompress(new_comp_data)
    decomp_ok = verify_decomp == bytes(new_block_raw)
    print(f"解压验证: {'✓' if decomp_ok else '✗'}")
    if not decomp_ok:
        print("错误: 重新压缩后解压验证失败！")
        return False

    # 重新计算块0 unknown 校验和
    new_block_header = struct.pack('<HHI', new_comp_size, old_orig, 0)  # unknown先用0占位
    new_unk = compute_block_checksum(new_block_header, new_comp_data)
    print(f"\n重新计算块校验和: 0x{new_unk:08x} (旧=0x{old_unk:08x})")

    # 构建新文件
    result = bytearray()
    result += old_data[:old_block_pos]  # header (68字节)
    # 块头：新的 comp_size + 保留原 orig_size + 新的 unknown
    block_header = struct.pack('<HHI', new_comp_size, old_orig, new_unk)
    result += block_header
    result += new_comp_data
    old_block_end = old_block_pos + 8 + old_comp
    result += old_data[old_block_end:]  # 后续块保持不变

    # 更新文件大小 (offset 0x20)
    struct.pack_into('<I', result, FILE_SIZE_OFFSET, len(result))
    print(f"文件大小: {len(old_data)} -> {len(result)}")

    # 重新计算头部 CRC32 (offset 0x40)
    new_crc = compute_header_crc(bytes(result))
    struct.pack_into('<I', result, HEADER_CRC_OFFSET, new_crc)
    print(f"头部CRC32: 0x{new_crc:08x}")

    # 保存
    if out_path is None:
        out_path = old_path.with_name(old_path.stem + '_patched.w3z')
    with open(out_path, 'wb') as f:
        f.write(bytes(result))
    print(f"\n补丁存档已保存: {out_path}")
    return True

def cmd_verify(w3z_path: pathlib.Path, max_blocks: int = 5):
    """验证存档完整性：文件大小、头部CRC32、各块校验和、块0解压、地图哈希"""
    data = w3z_path.read_bytes()
    hs = struct.unpack_from('<I', data, HEADER_SIZE_OFFSET)[0]
    num_blocks = struct.unpack_from('<I', data, NUM_BLOCKS_OFFSET)[0]
    file_size = struct.unpack_from('<I', data, FILE_SIZE_OFFSET)[0]
    header_crc = struct.unpack_from('<I', data, HEADER_CRC_OFFSET)[0]

    print(f"\n=== {w3z_path} ===")
    print(f"文件大小: {len(data)} (header.file_size={file_size}, "
          f"{'✓' if len(data) == file_size else '✗'})")
    print(f"块数: {num_blocks}")

    # 验证头部 CRC32
    calc_crc = compute_header_crc(data)
    print(f"头部CRC32: 文件=0x{header_crc:08x}, 计算=0x{calc_crc:08x}, "
          f"{'✓' if calc_crc == header_crc else '✗'}")

    # 验证各块校验和
    block_offset = hs
    all_ok = True
    for i in range(min(num_blocks, max_blocks)):
        if block_offset + 8 > len(data):
            break
        comp_size, orig_size, unknown = struct.unpack_from('<HHI', data, block_offset)
        if comp_size == 0:
            break
        comp_data = data[block_offset + 8:block_offset + 8 + comp_size]
        block_header = data[block_offset:block_offset + 8]
        calc_unk = compute_block_checksum(block_header, comp_data)
        ok = calc_unk == unknown
        if not ok:
            all_ok = False
        match = '✓' if ok else '✗'
        print(f"  块{i}: unknown 文件=0x{unknown:08x} 计算=0x{calc_unk:08x} {match}")
        block_offset += 8 + comp_size

    # 验证块0解压
    comp_size, orig_size, unknown = struct.unpack_from('<HHI', data, hs)
    comp_data = data[hs + 8:hs + 8 + comp_size]
    d = zlib.decompressobj(wbits=15)
    raw = d.decompress(comp_data)
    decomp_ok = len(raw) >= orig_size
    print(f"  块0解压: {len(raw)} 字节 (orig_size={orig_size}), "
          f"{'✓' if decomp_ok else '✗'}")

    # 显示地图哈希
    info = extract_map_info(raw)
    print(f"  地图路径: {info['map_path']}")
    print(f"  创建者:   {info['creator']}")
    print(f"  校验码(8字节): {info['map_checksum_8'].hex()}")
    print(f"  尾部哈希({len(info['trailing_hash'])}字节): {info['trailing_hash'].hex()}")

    print(f"\n{'=== 所有校验通过 ✓ ===' if all_ok and calc_crc == header_crc and len(data) == file_size else '=== 存在校验失败 ✗ ==='}")
    return all_ok and calc_crc == header_crc and len(data) == file_size


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        print("\n命令:")
        print(f"  python {sys.argv[0]} info <save.w3z>")
        print(f"  python {sys.argv[0]} extract <save.w3z>")
        print(f"  python {sys.argv[0]} replace <old_save.w3z> <new_save.w3z> [out.w3z]")
        print(f"  python {sys.argv[0]} verify <save.w3z>")
        return 1

    cmd = sys.argv[1]

    if cmd == 'info':
        cmd_info(pathlib.Path(sys.argv[2]))
    elif cmd == 'extract':
        cmd_extract(pathlib.Path(sys.argv[2]))
    elif cmd == 'replace':
        if len(sys.argv) < 4:
            print("Usage: replace <old_save.w3z> <new_save.w3z> [out.w3z]")
            return 1
        out_path = pathlib.Path(sys.argv[4]) if len(sys.argv) >= 5 else None
        cmd_replace(pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3]), out_path)
    elif cmd == 'verify':
        cmd_verify(pathlib.Path(sys.argv[2]))
    else:
        print(f"Unknown command: {cmd}")
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())
