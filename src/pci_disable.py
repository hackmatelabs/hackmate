from typing import Optional

_EXT_OP_PREFIX = 0x5B
_DEVICE_OP = 0x82
_NAME_OP = 0x08


def _is_valid_nameseg(raw: bytes) -> bool:
    if len(raw) != 4:
        return False
    first = raw[0]
    if not ((65 <= first <= 90) or first == 0x5F):
        return False
    for c in raw[1:]:
        if not ((65 <= c <= 90) or (48 <= c <= 57) or c == 0x5F):
            return False
    return True


def _decode_pkglen(data: bytes, pos: int) -> Optional[tuple[int, int]]:
    if pos >= len(data):
        return None
    b0 = data[pos]
    num_extra = b0 >> 6
    if num_extra == 0:
        return b0 & 0x3F, 1
    if pos + num_extra >= len(data):
        return None
    length = b0 & 0x0F
    for i in range(1, num_extra + 1):
        length |= data[pos + i] << (4 + 8 * (i - 1))
    return length, num_extra + 1


def _decode_integer(data: bytes, pos: int) -> Optional[tuple[int, int]]:
    if pos >= len(data):
        return None
    op = data[pos]
    if op == 0x00:
        return 0, 1
    if op == 0x01:
        return 1, 1
    if op == 0x0A and pos + 1 < len(data):
        return data[pos + 1], 2
    if op == 0x0B and pos + 2 < len(data):
        return int.from_bytes(data[pos + 1:pos + 3], "little"), 3
    if op == 0x0C and pos + 4 < len(data):
        return int.from_bytes(data[pos + 1:pos + 5], "little"), 5
    if op == 0x0E and pos + 8 < len(data):
        return int.from_bytes(data[pos + 1:pos + 9], "little"), 9
    return None


def _walk_devices(data: bytes, pos: int, end: int, path: list[str], results: dict[int, list[str]]) -> None:
    i = pos
    n = end
    while i < n - 1:
        if data[i] == _EXT_OP_PREFIX and data[i + 1] == _DEVICE_OP:
            pkg = _decode_pkglen(data, i + 2)
            if pkg:
                pkg_len, pkg_bytes = pkg
                pkglen_start = i + 2
                scope_end = min(pkglen_start + pkg_len, n)
                name_start = pkglen_start + pkg_bytes
                if name_start + 4 <= n and _is_valid_nameseg(data[name_start:name_start + 4]):
                    name = data[name_start:name_start + 4].decode("ascii")
                    body_start = name_start + 4
                    new_path = path + [name]

                    first_child = data.find(
                        bytes([_EXT_OP_PREFIX, _DEVICE_OP]), body_start, scope_end
                    )
                    own_body_end = first_child if first_child != -1 else scope_end
                    adr_pos = data.find(b"\x08_ADR", body_start, own_body_end)
                    if adr_pos != -1:
                        val = _decode_integer(data, adr_pos + 5)
                        if val:
                            results.setdefault(val[0], []).append(".".join(new_path))

                    _walk_devices(data, body_start, scope_end, new_path, results)
                    i = scope_end
                    continue
        i += 1


def find_device_path_by_pci_address(dsdt_data: bytes, device: int, function: int = 0) -> Optional[str]:
    target = (device << 16) | function
    results: dict[int, list[str]] = {}
    _walk_devices(dsdt_data, 0, len(dsdt_data), [], results)
    matches = results.get(target, [])
    if len(matches) != 1:
        return None
    return "_SB." + matches[0]


def build_disable_ssdt(device_path: str, table_id: str = "DSBL") -> str:
    return (
        f'DefinitionBlock ("", "SSDT", 2, "CORP", "{table_id}", 0x00000000)\n'
        "{\n"
        f"    External ({device_path}, DeviceObj)\n"
        f"    Scope ({device_path})\n"
        "    {\n"
        "        Method (_STA, 0, NotSerialized)\n"
        "        {\n"
        "            Return (Zero)\n"
        "        }\n"
        "    }\n"
        "}\n"
    )
