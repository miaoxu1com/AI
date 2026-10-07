# W3Z/W3V Container Format

## Scope

Use this reference for Warcraft III `.w3z` saved games and `.w3v` game-cache files such as `Campaigns.w3v` and chapter caches. These files share the Warcraft III recorded-game compressed container used by saves/replays/caches.

## Outer Layout

Known signature:

```text
Warcraft III recorded game\x1a\x00
```

Header starts at byte 0:

```text
0x00  28 bytes  signature
0x1C  u32       header_size
0x20  u32       file_size
0x24  u32       header_ver
0x28  u32       decompressed_size field from original header
0x2C  u32       block_count
0x30  ...       subheader bytes up to header_size
```

After the header, the file is a sequence of compressed blocks. Block header is 8 bytes:

```text
u16 compressed_size   (little-endian)
u16 original_size     (little-endian)
u32 unknown/flags
u8[compressed_size] zlib_payload
```

Block sizes by file type:
- **Replays (.w3g)**: original_size = 8192 (8 KiB) per block, except the final block
- **Saves (.w3z) and game caches (.w3v)**: original_size = 65535 (≈64 KiB) per block, except the final block

> **Note**: Earlier documentation incorrectly described a 12-byte block header with a per-block checksum. The actual block header is 8 bytes and there is no per-block checksum; the only checksum is the header CRC.

## Compression

Warcraft-compatible repacks observed in this workspace use:

```python
zlib.compressobj(level=1, wbits=15)
compressed = compressor.compress(chunk) + compressor.flush(zlib.Z_SYNC_FLUSH)
```

Using ordinary `zlib.compress()` may produce a file that decompresses in scripts but does not match Warcraft's expected block stream closely enough for save loading.

## Header CRC

For `header_ver == 1`, the header CRC field is at absolute offset `64`. Recompute CRC32 over the full header after zeroing that 4-byte field.

For `header_ver == 0`, the older offset is `48`.

Algorithm:

```python
header[crc_offset:crc_offset + 4] = b"\0\0\0\0"
crc = zlib.crc32(header) & 0xffffffff
struct.pack_into("<I", header, crc_offset, crc)
```

## Safe Modify Procedure

1. Back up the original `.w3z` or `.w3v`.
2. Unpack to raw with `scripts/w3z_tool.py unpack`.
3. Edit raw bytes only after identifying stable offsets or byte signatures.
4. Repack using the original file as template with `scripts/w3z_tool.py pack`.
5. Unpack the rebuilt file again and compare the raw output to the intended raw bytes.
6. Copy into the live profile only after verification.

## Visibility and Load-Screen Failures

If a save appears in the load list but cannot show basic info, the outer header CRC or block structure is usually malformed.

If a save does not appear at all, likely causes include:

- Wrong directory/profile.
- Wrong filename extension or save slot metadata.
- Bad signature/header.
- Unsupported build/version metadata inside the raw data.
- Repacked zlib stream/checksums not matching Warcraft's expectations.

First prove that an unmodified save can be exact-repacked or at least loadable-repacked before changing gameplay bytes.

## Useful Validation

```powershell
python <skill>\scripts\w3z_tool.py inspect .\n4d.w3z
python <skill>\scripts\w3z_tool.py unpack .\n4d.w3z .\n4d.raw.bin
python <skill>\scripts\w3z_tool.py pack .\n4d.w3z .\n4d.raw.bin .\n4d.repack.w3z
python <skill>\scripts\w3z_tool.py unpack .\n4d.repack.w3z .\n4d.repack.raw.bin
fc /b .\n4d.raw.bin .\n4d.repack.raw.bin
```
