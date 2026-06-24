"""
Minimal pure-Python parser for binary AndroidManifest.xml (AXML).
Extracts package, versionCode, versionName, minSdkVersion, and app label.
"""
import struct
from typing import Dict


_RES_STRING_POOL = 0x0001
_RES_XML_START_ELEMENT = 0x0102
_UTF8_FLAG = 0x0100
_NO_ENTRY = 0xFFFFFFFF

_TYPE_STRING = 0x03
_TYPE_INT_DEC = 0x10
_TYPE_INT_HEX = 0x11
_TYPE_INT_BOOL = 0x12


def _r32(d: bytes, o: int) -> int:
    return struct.unpack_from("<I", d, o)[0]


def _r16(d: bytes, o: int) -> int:
    return struct.unpack_from("<H", d, o)[0]


class _StrPool:
    def __init__(self, data: bytes, off: int):
        self.strings = []
        cnt = _r32(data, off + 8)
        flags = _r32(data, off + 16)
        str_start = _r32(data, off + 20)
        is_utf8 = bool(flags & _UTF8_FLAG)

        offsets = [_r32(data, off + 28 + i * 4) for i in range(cnt)]

        base = off + str_start
        for o in offsets:
            s = self._read_str(data, base + o, is_utf8)
            self.strings.append(s)

    def _read_str(self, data: bytes, off: int, utf8: bool) -> str:
        try:
            if utf8:
                return self._read_utf8(data, off)
            return self._read_utf16(data, off)
        except Exception:
            return ""

    def _read_utf16(self, data: bytes, off: int) -> str:
        clen = _r16(data, off)
        raw = data[off + 2:off + 2 + clen * 2]
        return raw.decode("utf-16-le", errors="replace")

    def _read_utf8(self, data: bytes, off: int) -> str:
        b = data[off]; off += 1
        if b & 0x80:
            _ = ((b & 0x7F) << 8) | data[off]; off += 1
        b = data[off]; off += 1
        if b & 0x80:
            blen = ((b & 0x7F) << 8) | data[off]; off += 1
        else:
            blen = b
        return data[off:off + blen].decode("utf-8", errors="replace")

    def __getitem__(self, idx: int) -> str:
        if 0 <= idx < len(self.strings):
            return self.strings[idx]
        return ""


def _attr_str(av: int, at: int, ad: int, pool: _StrPool) -> str:
    if av != _NO_ENTRY:
        return pool[av]
    if at == _TYPE_STRING and ad != _NO_ENTRY:
        return pool[ad]
    return ""


def _attr_int(at: int, ad: int) -> str:
    if at in (_TYPE_INT_DEC, _TYPE_INT_HEX, _TYPE_INT_BOOL):
        return str(ad)
    return ""


def parse_axml(data: bytes) -> Dict[str, str]:
    result = {"package": "", "version_code": "", "version_name": "", "min_sdk": "", "app_name": ""}
    if len(data) < 8 or _r16(data, 0) != 0x0003:
        return result

    pool = None
    elems = {}

    off = 8
    while off + 8 <= len(data):
        ctype = _r16(data, off)
        chdr = _r16(data, off + 2)
        csize = _r32(data, off + 4)
        if csize == 0:
            break
        if ctype == _RES_STRING_POOL and pool is None:
            pool = _StrPool(data, off)
        elif ctype == _RES_XML_START_ELEMENT and pool is not None:
            # ResXMLTree_attrExt starts after chunk header
            e_off = off + chdr
            # struct ResXMLTree_attrExt:
            #   lineNumber(4), ns(4), name(4),
            #   attributeStart(2), attributeSize(2), idIndex(2), classIndex(2), style(4)
            ns_idx = _r32(data, e_off + 4)
            name_idx = _r32(data, e_off + 8)
            attr_start = _r16(data, e_off + 12)
            attr_size = _r16(data, e_off + 14)

            tag = pool[name_idx]
            ns_uri = pool[ns_idx] if ns_idx != _NO_ENTRY else ""
            attrs = elems.setdefault(tag, [])

            data_end = off + csize
            a_off = e_off + attr_start
            while a_off + attr_size <= data_end:
                # ResXMLTree_attribute: ns(4), name(4), rawValue(4), Res_value { size(2), reserved(1), type(1), data(4) }
                an_ns = _r32(data, a_off)
                an_name = _r32(data, a_off + 4)
                raw_val = _r32(data, a_off + 8)
                val_size = _r16(data, a_off + 12)
                val_type = data[a_off + 14]
                val_data = _r32(data, a_off + 16)

                an_ns_uri = pool[an_ns] if an_ns != _NO_ENTRY else ""
                attrs.append((pool[an_name], an_ns_uri, raw_val, val_type, val_data))

                a_off += attr_size
        off += csize

    if pool is None:
        return result

    ns = "http://schemas.android.com/apk/res/android"

    for tag, attrs in elems.items():
        for aname, ans, av, at, ad in attrs:
            if tag == "manifest":
                if aname == "package" and ans == "":
                    s = _attr_str(av, at, ad, pool)
                    if s: result["package"] = s
                elif aname == "versionCode" and ans == ns and not result["version_code"]:
                    s = _attr_int(at, ad)
                    if s: result["version_code"] = s
                elif aname == "versionName" and ans == ns and not result["version_name"]:
                    s = _attr_str(av, at, ad, pool)
                    if s: result["version_name"] = s
            elif tag == "uses-sdk":
                if aname == "minSdkVersion" and ans == ns and not result["min_sdk"]:
                    s = _attr_int(at, ad)
                    if s: result["min_sdk"] = s
            elif tag == "application":
                if aname == "label" and ans == ns and not result["app_name"]:
                    s = _attr_str(av, at, ad, pool)
                    if s: result["app_name"] = s

    return result
