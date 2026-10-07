#!/usr/bin/env python3
"""
分析 w3z 文件的外层头部，寻找地图哈希字段
同时分析解压后的 raw 数据的前 1KB 结构
"""
import struct
import pathlib
import sys
import zlib

SIG = b"Warcraft III recorded game\x1a\x00"

def parse_w3z_header(data: bytes):
    """解析 w3z 外头部"""
    if data[:len(SIG)] != SIG:
        print("Bad signature!")
        return None
    
    header_size, file_size, header_ver, decomp_size, nblocks = struct.unpack_from("<5I", data, len(SIG))
    
    print(f"=== W3Z Outer Header ===")
    print(f"  Signature: {SIG}")
    print(f"  header_size: {header_size} (0x{header_size:x})")
    print(f"  file_size: {file_size} (0x{file_size:x})")
    print(f"  header_ver: {header_ver}")
    print(f"  decomp_size: {decomp_size} (0x{decomp_size:x})")
    print(f"  nblocks: {nblocks}")
    print(f"  actual file size: {len(data)}")
    
    # subheader
    subheader = data[48:header_size]
    print(f"\n=== Subheader ({len(subheader)} bytes) ===")
    
    # 按 DWORD 打印
    for i in range(0, len(subheader), 32):
        hex_bytes = ' '.join(f'{subheader[i+j]:02x}' for j in range(min(32, len(subheader)-i)))
        dwords = []
        for j in range(0, min(32, len(subheader)-i), 4):
            if i + j + 4 <= len(subheader):
                dwords.append(f'{struct.unpack_from("<I", subheader, i+j)[0]:08x}')
        ascii_str = ''.join(chr(subheader[i+j]) if 32 <= subheader[i+j] < 127 else '.' for j in range(min(32, len(subheader)-i)))
        print(f"  +0x{i:04x}: {hex_bytes}")
        print(f"           dwords: {' '.join(dwords)}")
        print(f"           ascii:  {ascii_str}")
    
    # 找 CRC 字段
    crc_off = 64 if header_ver == 1 else 48
    if len(subheader) >= crc_off + 4:
        crc_val = struct.unpack_from('<I', subheader, crc_off - 48)[0]
        print(f"\n  Header CRC (at offset {crc_off}): 0x{crc_val:08x}")
    
    return {
        'header_size': header_size,
        'header_ver': header_ver,
        'decomp_size': decomp_size,
        'nblocks': nblocks,
        'subheader': subheader,
    }

def analyze_raw_header(raw_data: bytes, size: int = 1024):
    """分析解压后 raw 数据的头部"""
    print(f"\n=== Raw Data Header (first {size} bytes) ===")
    data = raw_data[:size]
    
    for i in range(0, size, 16):
        hex_bytes = ' '.join(f'{data[i+j]:02x}' for j in range(min(16, size-i)))
        ascii_str = ''.join(chr(data[i+j]) if 32 <= data[i+j] < 127 else '.' for j in range(min(16, size-i)))
        print(f"  0x{i:04x}: {hex_bytes}  {ascii_str}")

def find_all_strings(raw_data: bytes, min_len=4, max_scan=200000):
    """在前 max_scan 字节中找所有可打印字符串"""
    print(f"\n=== All printable strings in first {max_scan} bytes ===")
    data = raw_data[:max_scan]
    
    current = bytearray()
    start = 0
    results = []
    for i, b in enumerate(data):
        if 32 <= b < 127:
            if not current:
                start = i
            current.append(b)
        else:
            if len(current) >= min_len:
                results.append((start, current.decode('ascii', errors='replace')))
            current = bytearray()
    if len(current) >= min_len:
        results.append((start, current.decode('ascii', errors='replace')))
    
    for off, s in results[:100]:
        print(f"  @0x{off:06x}: {s}")
    
    print(f"\n  Total: {len(results)} strings")
    return results

def main():
    if len(sys.argv) < 2:
        print("Usage: analyze_w3z_full.py <save.w3z>")
        return 1
    
    w3z_path = pathlib.Path(sys.argv[1])
    data = w3z_path.read_bytes()
    
    print(f"File: {w3z_path} ({len(data)} bytes)\n")
    
    # 分析外头部
    hdr = parse_w3z_header(data)
    if not hdr:
        return 1
    
    # 解压第一块数据
    header_size = hdr['header_size']
    off = header_size
    
    # 读第一个块
    comp_size, orig_size = struct.unpack_from("<HH", data, off)
    unknown = struct.unpack_from("<I", data, off + 4)[0]
    print(f"\n=== First Block ===")
    print(f"  comp_size: {comp_size}, orig_size: {orig_size}, unknown: 0x{unknown:08x}")
    
    comp_data = data[off+8:off+8+comp_size]
    decompressor = zlib.decompressobj(wbits=15)
    first_block = decompressor.decompress(comp_data)[:orig_size]
    print(f"  Decompressed: {len(first_block)} bytes")
    
    analyze_raw_header(first_block, 512)
    
    # 解压全部数据并分析前 50KB 的字符串
    print(f"\n=== Decompressing all blocks... ===")
    raw = bytearray()
    pos = header_size
    block_idx = 0
    while pos + 8 <= len(data):
        comp_size, orig_size = struct.unpack_from("<HH", data, pos)
        comp_data = data[pos+8:pos+8+comp_size]
        if comp_size == 0:
            raw += b'\x00' * orig_size
        else:
            decompressor = zlib.decompressobj(wbits=15)
            raw += decompressor.decompress(comp_data)[:orig_size]
        pos += 8 + comp_size
        block_idx += 1
    
    print(f"  Total decompressed: {len(raw)} bytes, {block_idx} blocks")
    
    find_all_strings(bytes(raw), min_len=4, max_scan=200000)

if __name__ == '__main__':
    sys.exit(main() or 0)
