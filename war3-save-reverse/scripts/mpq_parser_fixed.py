#!/usr/bin/env python3
"""
纯 Python MPQ 解析器（修正版）
参考：http://sfsrealm.hopto.org/inside_mopaq/index.htm
修复：
  1. prepare_crypt_table 算法
  2. hash_string 中的 +3
  3. decrypt_block 中缺失的 seed 更新
"""
import struct
import hashlib
import zlib
import pathlib
import sys

MPQ_MAGIC = b'MPQ\x1a'

MPQ_FILE_IMPLODE = 0x00000100
MPQ_FILE_COMPRESS = 0x00000200
MPQ_FILE_ENCRYPTED = 0x00010000
MPQ_FILE_FIX_KEY = 0x00020000
MPQ_FILE_SINGLE_UNIT = 0x01000000
MPQ_FILE_DELETE_MARKER = 0x02000000
MPQ_FILE_SECTOR_CRC = 0x04000000
MPQ_FILE_EXISTS = 0x80000000

MPQ_HASH_ENTRY_EMPTY = 0xFFFFFFFF
MPQ_HASH_ENTRY_DELETED = 0xFFFFFFFE

crypt_table = [0] * 0x500

def prepare_crypt_table():
    seed = 0x00100001
    for index1 in range(0x100):
        index2 = index1
        for i in range(5):
            seed = (seed * 125 + 3) % 0x2AAAAB
            temp1 = (seed & 0xFFFF) << 0x10
            seed = (seed * 125 + 3) % 0x2AAAAB
            temp2 = (seed & 0xFFFF)
            crypt_table[index2] = (temp1 | temp2) & 0xFFFFFFFF
            index2 += 0x100

def hash_string(name: str, hash_type: int) -> int:
    seed1 = 0x7FED7FED
    seed2 = 0xEEEEEEEE
    for c in name.upper():
        ch = ord(c)
        if ch == ord('/'):
            ch = ord('\\')
        seed1 = (crypt_table[hash_type * 0x100 + ch] ^ ((seed1 + seed2) & 0xFFFFFFFF)) & 0xFFFFFFFF
        seed2 = ((ch + seed1 + seed2 + (seed2 << 5) + 3) & 0xFFFFFFFF)
    return seed1

def decrypt_block(data: bytes, key: int) -> bytes:
    result = bytearray(len(data))
    seed = 0xEEEEEEEE
    pos = 0
    length = len(data) // 4

    for i in range(length):
        seed = (seed + crypt_table[0x400 + (key & 0xFF)]) & 0xFFFFFFFF
        value = struct.unpack_from('<I', data, pos)[0]
        ch = value ^ ((key + seed) & 0xFFFFFFFF)

        key = (((key ^ 0xFFFFFFFF) << 0x15) + 0x11111111) & 0xFFFFFFFF
        key = (key | (key >> 0x1B if False else (key >> 0x0B))) & 0xFFFFFFFF
        key = ((((key ^ 0xFFFFFFFF) << 0x15) + 0x11111111) & 0xFFFFFFFF) | ((key >> 0x0B) & 0xFFFFFFFF)

        seed = (ch + seed + (seed << 5) + 3) & 0xFFFFFFFF

        struct.pack_into('<I', result, pos, ch)
        pos += 4

    return bytes(result)

def decrypt_block_clean(data: bytes, key: int) -> bytes:
    result = bytearray(len(data))
    seed = 0xEEEEEEEE
    pos = 0
    length = len(data) // 4

    for i in range(length):
        seed = (seed + crypt_table[0x400 + (key & 0xFF)]) & 0xFFFFFFFF
        value = struct.unpack_from('<I', data, pos)[0]
        ch = value ^ ((key + seed) & 0xFFFFFFFF)

        not_key = key ^ 0xFFFFFFFF
        shifted = (not_key << 0x15) & 0xFFFFFFFF
        added = (shifted + 0x11111111) & 0xFFFFFFFF
        key = (added | (key >> 0x0B)) & 0xFFFFFFFF

        seed = (ch + seed + (seed << 5) + 3) & 0xFFFFFFFF

        struct.pack_into('<I', result, pos, ch)
        pos += 4

    return bytes(result)

def parse_mpq(data: bytes, mpq_off: int) -> dict:
    prepare_crypt_table()

    if data[mpq_off:mpq_off+4] != MPQ_MAGIC:
        return None

    header_size = struct.unpack_from('<I', data, mpq_off + 4)[0]
    archive_size = struct.unpack_from('<I', data, mpq_off + 8)[0]
    sector_shift = struct.unpack_from('<H', data, mpq_off + 0x0e)[0]
    hash_table_off = struct.unpack_from('<I', data, mpq_off + 0x10)[0]
    block_table_off = struct.unpack_from('<I', data, mpq_off + 0x14)[0]
    hash_table_count = struct.unpack_from('<I', data, mpq_off + 0x18)[0]
    block_table_count = struct.unpack_from('<I', data, mpq_off + 0x1c)[0]

    sector_size = 512 << sector_shift
    abs_hash_off = mpq_off + hash_table_off
    abs_block_off = mpq_off + block_table_off

    hash_key = hash_string("(hash table)", 3)
    block_key = hash_string("(block table)", 3)

    raw_hash_data = data[abs_hash_off:abs_hash_off + hash_table_count * 16]
    decrypted_hash = decrypt_block_clean(raw_hash_data, hash_key)

    hash_table = []
    for i in range(hash_table_count):
        off = i * 16
        entry = struct.unpack_from('<IIHHI', decrypted_hash, off)
        hash_table.append({
            'name_a': entry[0],
            'name_b': entry[1],
            'language': entry[2],
            'platform': entry[3],
            'block_idx': entry[4],
        })

    raw_block_data = data[abs_block_off:abs_block_off + block_table_count * 16]
    decrypted_block = decrypt_block_clean(raw_block_data, block_key)

    block_table = []
    for i in range(block_table_count):
        off = i * 16
        entry = struct.unpack_from('<IIII', decrypted_block, off)
        block_table.append({
            'offset': entry[0],
            'comp_size': entry[1],
            'uncomp_size': entry[2],
            'flags': entry[3],
        })

    print(f"  Sector size: {sector_size}")
    print(f"  Hash table: {hash_table_count} entries (key=0x{hash_key:08x})")
    print(f"  Block table: {block_table_count} entries (key=0x{block_key:08x})")

    empty_count = sum(1 for e in hash_table if e['block_idx'] == MPQ_HASH_ENTRY_EMPTY)
    deleted_count = sum(1 for e in hash_table if e['block_idx'] == MPQ_HASH_ENTRY_DELETED)
    valid_count = hash_table_count - empty_count - deleted_count
    print(f"  Hash entries: {valid_count} valid, {empty_count} empty, {deleted_count} deleted")

    return {
        'mpq_off': mpq_off,
        'sector_size': sector_size,
        'hash_table': hash_table,
        'block_table': block_table,
        'hash_table_count': hash_table_count,
        'block_table_count': block_table_count,
        'data': data,
    }

def find_file(mpq: dict, filename: str) -> dict:
    hash_a = hash_string(filename, 1)
    hash_b = hash_string(filename, 2)
    table_hash = hash_string(filename, 0)

    count = mpq['hash_table_count']
    start = table_hash % count

    for i in range(count):
        idx = (start + i) % count
        entry = mpq['hash_table'][idx]
        if entry['name_a'] == hash_a and entry['name_b'] == hash_b:
            if entry['block_idx'] == MPQ_HASH_ENTRY_EMPTY:
                return None
            return entry
        if entry['block_idx'] == MPQ_HASH_ENTRY_EMPTY:
            return None

    return None

def extract_file(mpq: dict, filename: str) -> bytes:
    entry = find_file(mpq, filename)
    if entry is None:
        return None

    block = mpq['block_table'][entry['block_idx']]
    data = mpq['data']
    mpq_off = mpq['mpq_off']
    file_off = mpq_off + block['offset']
    comp_size = block['comp_size']
    uncomp_size = block['uncomp_size']
    flags = block['flags']

    if not (flags & MPQ_FILE_EXISTS):
        return None

    file_data = data[file_off:file_off + comp_size]

    if flags & MPQ_FILE_ENCRYPTED:
        enc_key = hash_string(filename, 3)
        if flags & MPQ_FILE_FIX_KEY:
            enc_key = (enc_key + block['offset']) & 0xFFFFFFFF
            enc_key = (enc_key ^ block['uncomp_size']) & 0xFFFFFFFF

        if flags & MPQ_FILE_SINGLE_UNIT:
            file_data = decrypt_block_clean(file_data, enc_key)
        else:
            file_data = decrypt_block_clean(file_data, enc_key)

    if flags & MPQ_FILE_SINGLE_UNIT:
        if flags & (MPQ_FILE_COMPRESS | MPQ_FILE_IMPLODE):
            try:
                if file_data[0] == 0x02:
                    return zlib.decompress(file_data[1:])
            except:
                pass
            try:
                return zlib.decompress(file_data)
            except:
                return file_data[:uncomp_size]
        return file_data[:uncomp_size]

    sector_size = mpq['sector_size']
    num_sectors = (uncomp_size + sector_size - 1) // sector_size

    if flags & (MPQ_FILE_COMPRESS | MPQ_FILE_IMPLODE):
        sector_offsets = []
        for i in range(num_sectors + 1):
            off = struct.unpack_from('<I', file_data, i * 4)[0]
            sector_offsets.append(off)

        result = bytearray()
        for i in range(num_sectors):
            sec_start = sector_offsets[i]
            sec_end = sector_offsets[i + 1]
            sec_data = file_data[sec_start:sec_end]
            expected_size = min(sector_size, uncomp_size - i * sector_size)

            if len(sec_data) == expected_size:
                result.extend(sec_data)
            elif len(sec_data) == 0:
                pass
            else:
                if len(sec_data) > 0:
                    comp_byte = sec_data[0]
                    try:
                        if comp_byte == 0x02:
                            result.extend(zlib.decompress(sec_data[1:]))
                        else:
                            result.extend(zlib.decompress(sec_data))
                    except:
                        result.extend(sec_data)

        return bytes(result[:uncomp_size])
    else:
        return file_data[:uncomp_size]

def main():
    if len(sys.argv) < 2:
        map_path = pathlib.Path("终焉王座.w3x")
    else:
        map_path = pathlib.Path(sys.argv[1])
    
    map_data = map_path.read_bytes()
    mpq_off = map_data.find(MPQ_MAGIC)
    print(f"Map: {map_path} ({len(map_data)} bytes), MPQ at 0x{mpq_off:x}")

    mpq = parse_mpq(map_data, mpq_off)
    if not mpq:
        print("Failed to parse MPQ!")
        return

    MAP_FILES = [
        "war3map.j",
        "war3map.w3e",
        "war3map.wpm",
        "war3map.doo",
        "war3map.w3u",
        "war3map.w3b",
        "war3map.w3d",
        "war3map.w3a",
        "war3map.w3q",
        "war3map.w3i",
        "(listfile)",
    ]

    print(f"\n=== Extracting files ===")
    found_count = 0
    for filename in MAP_FILES:
        data = extract_file(mpq, filename)
        if data is None:
            print(f"  {filename}: NOT FOUND")
            continue
        found_count += 1
        sha1 = hashlib.sha1(data).hexdigest()
        crc32_val = zlib.crc32(data) & 0xFFFFFFFF
        print(f"  {filename}: {len(data)} bytes, SHA1={sha1}, CRC32={crc32_val:08x}")
    
    print(f"\nFound {found_count}/{len(MAP_FILES)} files")

    if len(sys.argv) >= 3:
        save_raw_path = pathlib.Path(sys.argv[2])
        print(f"\n=== Loading save data and searching hashes ===")
        save_data = save_raw_path.read_bytes()
        print(f"Save data: {len(save_data)} bytes")
        
        all_hashes = {}
        for filename in MAP_FILES:
            data = extract_file(mpq, filename)
            if data is None:
                continue
            sha1 = hashlib.sha1(data).digest()
            crc = struct.pack('<I', zlib.crc32(data) & 0xFFFFFFFF)
            all_hashes[f"{filename}_sha1_le"] = sha1
            all_hashes[f"{filename}_sha1_be"] = sha1[::-1]
            all_hashes[f"{filename}_crc32_le"] = crc
            all_hashes[f"{filename}_crc32_be"] = crc[::-1]
        
        found_any = False
        for label, h in all_hashes.items():
            pos = save_data.find(h)
            if pos != -1:
                print(f"  [FOUND] {label}: at offset 0x{pos:x}")
                found_any = True
        if not found_any:
            print("  No per-file hashes found in save data")

if __name__ == '__main__':
    main()
