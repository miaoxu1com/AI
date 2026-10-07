#!/usr/bin/env python3
import argparse
import pathlib
import struct
import sys
import zlib

SIG = b"Warcraft III recorded game\x1a\x00"
BLOCK_SIZE_W3G = 8192
BLOCK_SIZE_W3Z = 65535


def parse_header(data: bytes) -> dict:
    if len(data) < 48:
        raise ValueError("file is too small for Warcraft III save header")
    if data[: len(SIG)] != SIG:
        raise ValueError("bad signature")
    header_size, file_size, header_ver, decomp_size, nblocks = struct.unpack_from("<5I", data, len(SIG))
    if header_size < 48 or header_size > len(data):
        raise ValueError(f"bad header_size: {header_size}")
    return {
        "header_size": header_size,
        "file_size": file_size,
        "header_ver": header_ver,
        "decomp_size": decomp_size,
        "nblocks": nblocks,
        "subheader": bytearray(data[48:header_size]),
    }


def write_header_crc(header: bytearray, header_ver: int) -> bytearray:
    crc_off = 64 if header_ver == 1 else 48
    if len(header) >= crc_off + 4:
        header[crc_off : crc_off + 4] = b"\x00\x00\x00\x00"
        crc = zlib.crc32(header) & 0xFFFFFFFF
        struct.pack_into("<I", header, crc_off, crc)
    return header


def iter_blocks(data: bytes, header_size: int):
    off = header_size
    block_idx = 0
    while off + 8 <= len(data):
        comp_size, orig_size = struct.unpack_from("<HH", data, off)
        unknown = struct.unpack_from("<I", data, off + 4)[0]
        payload_off = off + 8
        payload_end = payload_off + comp_size
        if payload_end > len(data):
            raise ValueError(f"block {block_idx}: compressed payload extends beyond file")
        yield block_idx, off, comp_size, orig_size, unknown, data[payload_off:payload_end]
        off = payload_end
        block_idx += 1


def inspect(path: pathlib.Path) -> None:
    data = path.read_bytes()
    meta = parse_header(data)
    print(f"path: {path}")
    print(f"header_size: {meta['header_size']}")
    print(f"file_size_header: {meta['file_size']}")
    print(f"file_size_actual: {len(data)}")
    print(f"header_ver: {meta['header_ver']}")
    print(f"decomp_size_header: {meta['decomp_size']}")
    print(f"nblocks: {meta['nblocks']}")
    total_orig = 0
    total_comp = 0
    block_count = 0
    for index, off, comp_size, orig_size, unknown, comp_data in iter_blocks(
        data, meta["header_size"]
    ):
        total_orig += orig_size
        total_comp += comp_size
        block_count += 1
        if index < 5 or index >= meta["nblocks"] - 2:
            print(
                f"block {index}: off=0x{off:x} comp={comp_size} "
                f"orig={orig_size} unknown=0x{unknown:08x}"
            )
        elif index == 5 and meta["nblocks"] > 7:
            print("...")
    print(f"total blocks counted: {block_count}")
    print(f"decompressed_size_blocks: {total_orig}")
    print(f"compressed_size_blocks: {total_comp}")


def unpack(save_path: pathlib.Path, raw_path: pathlib.Path) -> None:
    data = save_path.read_bytes()
    meta = parse_header(data)
    raw = bytearray()
    for index, off, comp_size, orig_size, unknown, comp_data in iter_blocks(
        data, meta["header_size"]
    ):
        if comp_size == 0:
            raw += b"\x00" * orig_size
        else:
            decompressor = zlib.decompressobj(wbits=15)
            chunk = decompressor.decompress(comp_data)
            if len(chunk) < orig_size:
                raise ValueError(
                    f"block {index} short decompress: got {len(chunk)}, expected {orig_size}"
                )
            raw += chunk[:orig_size]
    raw_path.write_bytes(raw)
    print(f"Unpacked {len(raw)} bytes to {raw_path}")


def pack(template_path: pathlib.Path, raw_path: pathlib.Path, out_path: pathlib.Path) -> None:
    template = template_path.read_bytes()
    meta = parse_header(template)
    raw = raw_path.read_bytes()

    first_orig = 0
    for _, _, _, orig_size, _, _ in iter_blocks(template, meta["header_size"]):
        first_orig = orig_size
        break

    block_size = first_orig if first_orig > 0 else BLOCK_SIZE_W3Z
    if block_size not in (BLOCK_SIZE_W3G, BLOCK_SIZE_W3Z):
        print(f"Warning: unusual block size {block_size}, using as-is")

    blocks = []
    for start in range(0, len(raw), block_size):
        chunk = raw[start : start + block_size]
        if len(chunk) < block_size:
            chunk = chunk + b"\x00" * (block_size - len(chunk))

        compressor = zlib.compressobj(level=1, wbits=15)
        comp = compressor.compress(chunk) + compressor.flush(zlib.Z_SYNC_FLUSH)
        blocks.append((comp, len(chunk), 0))

    total_size = meta["header_size"] + sum(8 + len(comp) for comp, _, _ in blocks)

    header = bytearray()
    header += SIG
    header += struct.pack(
        "<5I",
        meta["header_size"],
        total_size,
        meta["header_ver"],
        meta["decomp_size"],
        len(blocks),
    )
    header += meta["subheader"]
    out = bytearray(write_header_crc(header, meta["header_ver"]))

    for comp, orig_size, unknown in blocks:
        out += struct.pack("<HHI", len(comp), orig_size, unknown)
        out += comp

    out_path.write_bytes(out)
    print(f"Packed {len(out)} bytes to {out_path}")


def scan_rawcodes(raw_path: pathlib.Path, codes: list[str], context: int) -> None:
    import re
    data = raw_path.read_bytes()
    if not codes:
        candidates = sorted(set(re.findall(rb"[A-Za-z0-9][A-Za-z0-9][A-Za-z0-9][A-Za-z0-9]", data)))
        for code in candidates:
            print(code.decode("ascii", errors="replace"))
        return
    for code in codes:
        needle = code.encode("ascii")
        start = 0
        while True:
            pos = data.find(needle, start)
            if pos < 0:
                break
            lo = max(0, pos - context)
            hi = min(len(data), pos + len(needle) + context)
            snippet = data[lo:hi]
            printable = "".join(chr(b) if 32 <= b <= 126 else "." for b in snippet)
            print(f"{code} @ 0x{pos:x}: {printable}")
            start = pos + 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect, unpack, repack, and scan Warcraft III .w3z/.w3v containers.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("inspect")
    p.add_argument("save")

    p = sub.add_parser("unpack")
    p.add_argument("save")
    p.add_argument("raw_output")

    p = sub.add_parser("pack")
    p.add_argument("template")
    p.add_argument("raw")
    p.add_argument("output")

    p = sub.add_parser("scan-rawcodes")
    p.add_argument("raw")
    p.add_argument("codes", nargs="*")
    p.add_argument("--context", type=int, default=32)

    args = parser.parse_args()
    if args.cmd == "inspect":
        inspect(pathlib.Path(args.save))
    elif args.cmd == "unpack":
        unpack(pathlib.Path(args.save), pathlib.Path(args.raw_output))
    elif args.cmd == "pack":
        pack(pathlib.Path(args.template), pathlib.Path(args.raw), pathlib.Path(args.output))
    elif args.cmd == "scan-rawcodes":
        scan_rawcodes(pathlib.Path(args.raw), args.codes, args.context)
    else:
        parser.print_help()
        return 2


if __name__ == "__main__":
    sys.exit(main())
