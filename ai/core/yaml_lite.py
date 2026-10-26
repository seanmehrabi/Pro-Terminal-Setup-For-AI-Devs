"""Minimal YAML subset parser (stdlib only, 2-space indent)."""

from __future__ import annotations

from typing import Any, List, Optional, Tuple, Union


class YamlLiteError(ValueError):
    pass


def parse(text: str) -> Any:
    """Parse a YAML document into Python objects."""
    lines = _tokenize_lines(text)
    if not lines:
        return None
    value, _ = _parse_node(lines, 0, lines[0][0])
    return value


def _tokenize_lines(text: str) -> List[Tuple[int, str]]:
    out: List[Tuple[int, str]] = []
    for raw in text.splitlines():
        line = _strip_comment(raw)
        if not line.strip():
            continue
        spaces = len(line) - len(line.lstrip(" "))
        if spaces % 2 != 0:
            raise YamlLiteError("Indent must use multiples of 2 spaces: {!r}".format(raw))
        content = line.strip()
        if content.startswith("{") or content.startswith("[") or "|" in content or "&" in content:
            raise YamlLiteError("Unsupported YAML feature in line: {!r}".format(raw))
        out.append((spaces // 2, content))
    return out


def _strip_comment(line: str) -> str:
    in_single = False
    in_double = False
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            return line[:i].rstrip()
        i += 1
    return line.rstrip()


def _parse_node(
    lines: List[Tuple[int, str]], index: int, level: int
) -> Tuple[Any, int]:
    if index >= len(lines):
        raise YamlLiteError("Unexpected end of document")
    cur_level, content = lines[index]
    if cur_level != level:
        raise YamlLiteError("Indent mismatch at {!r}".format(content))
    if content.startswith("- "):
        return _parse_list(lines, index, level)
    if ":" in content:
        return _parse_map(lines, index, level)
    raise YamlLiteError("Expected map or list at level {}, got {!r}".format(level, content))


def _parse_list(
    lines: List[Tuple[int, str]], index: int, level: int
) -> Tuple[List[Any], int]:
    items: List[Any] = []
    i = index
    while i < len(lines):
        cur_level, content = lines[i]
        if cur_level < level:
            break
        if cur_level != level or not content.startswith("- "):
            break
        rest = content[2:].strip()
        if not rest:
            raise YamlLiteError("Empty list item at line {!r}".format(content))
        if rest.startswith("- "):
            raise YamlLiteError("Nested list syntax not supported: {!r}".format(content))
        if ":" in rest and not _is_quoted_scalar(rest):
            key, _, after = rest.partition(":")
            key = key.strip()
            after = after.strip()
            if key:
                if after:
                    item = {key: _parse_scalar(after)}
                    i += 1
                    if i < len(lines) and lines[i][0] > level:
                        nested, i = _parse_map(lines, i, level + 1)
                        item.update(nested)
                    items.append(item)
                    continue
                nested, i = _parse_map(lines, i, level + 1)
                items.append(nested)
                continue
        items.append(_parse_scalar(rest))
        i += 1
    return items, i


def _parse_map(
    lines: List[Tuple[int, str]], index: int, level: int
) -> Tuple[dict, int]:
    result: dict = {}
    i = index
    while i < len(lines):
        cur_level, content = lines[i]
        if cur_level < level:
            break
        if cur_level != level:
            break
        if content.startswith("- "):
            break
        if ":" not in content:
            raise YamlLiteError("Expected key: value, got {!r}".format(content))
        key, _, value_part = content.partition(":")
        key = key.strip()
        if not key:
            raise YamlLiteError("Empty map key in {!r}".format(content))
        value_part = value_part.strip()
        if value_part:
            result[key] = _parse_scalar(value_part)
            i += 1
            continue
        i += 1
        if i < len(lines) and lines[i][0] > level:
            child, i = _parse_node(lines, i, level + 1)
            result[key] = child
        else:
            result[key] = None
    return result, i


def _is_quoted_scalar(text: str) -> bool:
    return (
        (text.startswith('"') and text.endswith('"'))
        or (text.startswith("'") and text.endswith("'"))
    )


def _parse_scalar(text: str) -> Union[str, int, float, bool, None]:
    if not text:
        return ""
    if _is_quoted_scalar(text):
        inner = text[1:-1]
        if text[0] == '"':
            return inner.replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")
        return inner
    lower = text.lower()
    if lower == "null" or lower == "~":
        return None
    if lower == "true":
        return True
    if lower == "false":
        return False
    if text.isdigit() or (text.startswith("-") and text[1:].isdigit()):
        return int(text)
    try:
        if any(ch in text for ch in ".eE"):
            return float(text)
    except ValueError:
        pass
    return text
