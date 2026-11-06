from __future__ import annotations

import argparse
import bz2
import hashlib
import lzma
from pathlib import Path

import requests


URL = (
    "https://bigota.d.miui.com/OS3.0.307.0.WOYCNXM/"
    "muyu-ota_full-OS3.0.307.0.WOYCNXM-user-16.0-2154ce3df2.zip"
)
TOTAL_SIZE = 8_702_157_559
PAYLOAD_ZIP_OFFSET = 4_822
PAYLOAD_DATA_BASE = PAYLOAD_ZIP_OFFSET + 24 + 306_215 + 267
MANIFEST = b""
EXPECTED_MANIFEST_SHA256 = "1239c7de106c4d5cb3d8645a7010cd5dca61e93124eb05089a9529959e55e552"
EXPECTED_IMAGE_SHA256 = "9dd01ed3e7e2097ea324f2a0fe75bc17fbe8ba2609973c6f1c17048dafe6c1a6"


def read_varint(data: bytes, offset: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while True:
        byte = data[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if byte < 0x80:
            return value, offset
        shift += 7
        if shift > 70:
            raise ValueError("invalid protobuf varint")


def fields(data: bytes):
    offset = 0
    while offset < len(data):
        tag, offset = read_varint(data, offset)
        number = tag >> 3
        wire_type = tag & 7
        if wire_type == 0:
            value, offset = read_varint(data, offset)
        elif wire_type == 1:
            value = data[offset : offset + 8]
            offset += 8
        elif wire_type == 2:
            length, offset = read_varint(data, offset)
            value = data[offset : offset + length]
            offset += length
        elif wire_type == 5:
            value = data[offset : offset + 4]
            offset += 4
        else:
            raise ValueError(f"unsupported protobuf wire type {wire_type}")
        yield number, wire_type, value


def int_field(message: bytes, number: int, default: int = 0) -> int:
    values = [
        value
        for field_number, wire_type, value in fields(message)
        if field_number == number and wire_type == 0
    ]
    return values[-1] if values else default


def bytes_fields(message: bytes, number: int) -> list[bytes]:
    return [
        value
        for field_number, wire_type, value in fields(message)
        if field_number == number and wire_type == 2
    ]


def find_init_boot_partition() -> tuple[int, list[bytes], bytes]:
    block_size = int_field(MANIFEST, 3, 4096)
    for raw_partition in bytes_fields(MANIFEST, 13):
        names = bytes_fields(raw_partition, 1)
        if not names or names[0].decode("utf-8", "replace") != "init_boot":
            continue
        operations = bytes_fields(raw_partition, 8)
        partition_info = bytes_fields(raw_partition, 7)
        expected_hash = b""
        if partition_info:
            hashes = bytes_fields(partition_info[0], 2)
            if hashes:
                expected_hash = hashes[0]
        return block_size, operations, expected_hash
    raise RuntimeError("init_boot partition not found")


def fetch_range(start: int, length: int) -> bytes:
    end = start + length - 1
    headers = {
        "Range": f"bytes={start}-{end}",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/140 Safari/537.36"
        ),
        "Referer": "https://xiaomihive.com/firmware/muyu/",
    }
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            with requests.get(URL, headers=headers, timeout=(30, 180), stream=True) as response:
                response.raise_for_status()
                expected_range = f"bytes {start}-{end}/{TOTAL_SIZE}"
                if response.status_code != 206 or response.headers.get("Content-Range") != expected_range:
                    raise RuntimeError(f"unexpected range response: {response.status_code} {response.headers.get('Content-Range')}")
                content = bytearray()
                for chunk in response.iter_content(chunk_size=65536):
                    content.extend(chunk)
                    if len(content) > length:
                        raise RuntimeError(f"range {start}-{end} exceeded {length} bytes")
                if len(content) != length:
                    raise RuntimeError(f"range {start}-{end}: expected {length}, got {len(content)}")
                return bytes(content)
        except Exception as error:
            last_error = error
            print(f"range retry {attempt}/3: {error}")
    raise RuntimeError(f"failed to fetch range {start}-{end}") from last_error


def decode_operation(operation: bytes, operation_index: int) -> tuple[int, bytes]:
    operation_type = int_field(operation, 1)
    data_offset = int_field(operation, 2)
    data_length = int_field(operation, 3)
    dst_extents = []
    for raw_extent in bytes_fields(operation, 6):
        dst_extents.append(
            (int_field(raw_extent, 1), int_field(raw_extent, 2))
        )
    expected_hashes = bytes_fields(operation, 8)
    expected_hash = expected_hashes[0] if expected_hashes else b""

    compressed = fetch_range(PAYLOAD_DATA_BASE + data_offset, data_length)
    actual_hash = hashlib.sha256(compressed).digest()
    if expected_hash and actual_hash != expected_hash:
        raise RuntimeError(
            f"operation {operation_index} SHA-256 mismatch: "
            f"{actual_hash.hex()} != {expected_hash.hex()}"
        )

    if operation_type == 0:  # REPLACE
        decoded = compressed
    elif operation_type == 1:  # REPLACE_BZ
        decoded = bz2.decompress(compressed)
    elif operation_type == 8:  # REPLACE_XZ
        decoded = lzma.decompress(compressed)
    elif operation_type == 6:  # ZERO
        decoded = b""
    else:
        raise RuntimeError(
            f"unsupported operation type {operation_type} at operation "
            f"{operation_index}"
        )

    expected_size = sum(block_count for _, block_count in dst_extents) * 4096
    if operation_type != 6 and len(decoded) != expected_size:
        raise RuntimeError(
            f"operation {operation_index}: decoded {len(decoded)} bytes, "
            f"expected {expected_size}"
        )
    print(
        f"operation {operation_index}: type={operation_type}, "
        f"compressed={data_length}, decoded={len(decoded)}, "
        f"extents={dst_extents}"
    )
    return operation_type, decoded


def main() -> None:
    global MANIFEST
    parser = argparse.ArgumentParser(description="Extract init_boot from the specific muyu OS3.0.307 OTA")
    parser.add_argument("--output", required=True, type=Path, help="output image path; parent directory must exist")
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Output already exists; choose a new path")
    MANIFEST = fetch_range(PAYLOAD_ZIP_OFFSET + 24, 306_215)
    manifest_hash = hashlib.sha256(MANIFEST).hexdigest()
    if manifest_hash != EXPECTED_MANIFEST_SHA256:
        raise RuntimeError(f"manifest SHA-256 mismatch: {manifest_hash}")
    block_size, operations, expected_image_hash = find_init_boot_partition()
    if block_size != 4096:
        raise RuntimeError(f"unexpected block size: {block_size}")
    if not operations:
        raise RuntimeError("init_boot has no operations")

    image = bytearray()
    for operation_index, operation in enumerate(operations):
        operation_type, decoded = decode_operation(operation, operation_index)
        chunk_offset = 0
        for raw_extent in bytes_fields(operation, 6):
            start_block = int_field(raw_extent, 1)
            block_count = int_field(raw_extent, 2)
            extent_size = block_count * block_size
            destination_offset = start_block * block_size
            if operation_type == 6:
                chunk = bytes(extent_size)
            else:
                chunk = decoded[chunk_offset : chunk_offset + extent_size]
                chunk_offset += extent_size
            required_size = destination_offset + len(chunk)
            if len(image) < required_size:
                image.extend(bytes(required_size - len(image)))
            image[destination_offset : required_size] = chunk

    image_hash = hashlib.sha256(image).digest()
    if expected_image_hash and image_hash != expected_image_hash:
        raise RuntimeError(
            f"final init_boot SHA-256 mismatch: "
            f"{image_hash.hex()} != {expected_image_hash.hex()}"
        )
    if image_hash.hex() != EXPECTED_IMAGE_SHA256:
        raise RuntimeError("image does not match the expected build")
    with args.output.open("xb") as output_file:
        output_file.write(image)
    print(f"saved={args.output}")
    print(f"size={len(image)}")
    print(f"sha256={image_hash.hex()}")


if __name__ == "__main__":
    main()
