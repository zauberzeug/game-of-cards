"""Minimal YAML subset parser — round-trips goc card frontmatter with no deps.

Public API:
    safe_load(text: str) -> dict | list | None

Accepted YAML features (driven by what goc/engine.py emits and reads):
  - Top-level block mapping with simple string keys
  - Scalar values: null/~, bool (true/false/yes/no), integer, ISO date string,
    plain string, single-quoted string, double-quoted string (with \\ \\n escapes)
  - Inline flow list: [a, b, c]
  - Inline flow map: {k: v, k2: v2}
  - Block literal scalar: | and |-
  - Block sequence: - item (items may be scalars or block maps)
  - Block mapping value at next indent level
  - # comments on their own lines or at end of lines

Unsupported (raises ParseError):
  - Anchors (&foo), aliases (*foo), tags (!!str)
  - Multi-document streams
  - Folded scalars (>)
  - Tabs as indentation
"""

from __future__ import annotations

import re
from typing import Any


class ParseError(ValueError):
    pass


_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_INT_RE = re.compile(r"^-?\d+$")
_NULL_SET = frozenset(("null", "Null", "NULL", "~"))
_TRUE_SET = frozenset(("true", "True", "TRUE", "yes", "Yes", "YES"))
_FALSE_SET = frozenset(("false", "False", "FALSE", "no", "No", "NO"))


# ── Public entry point ────────────────────────────────────────────────────────

def safe_load(text: str) -> Any:
    """Parse a YAML document. Returns dict, list, or None."""
    return _Parser(text.splitlines()).parse()


# ── Parser ────────────────────────────────────────────────────────────────────

class _Parser:
    def __init__(self, lines: list[str]):
        self._lines = lines
        self._pos = 0

    def parse(self) -> Any:
        line = self._peek()
        if line is None:
            return None
        bare = line.lstrip()
        if bare.startswith("&") or bare.startswith("*") or bare.startswith("!"):
            raise ParseError(f"line {self._pos + 1}: anchors/aliases/tags not supported")
        if bare.startswith("- ") or bare == "-":
            return self._parse_block_sequence(self._indent(line))
        return self._parse_block_mapping(self._indent(line))

    # ── Line helpers ──────────────────────────────────────────────────────────

    def _peek(self) -> str | None:
        """Return first non-blank, non-comment line; advance past skipped lines."""
        while self._pos < len(self._lines):
            line = self._lines[self._pos]
            bare = line.rstrip().lstrip()
            if bare and not bare.startswith("#"):
                return self._lines[self._pos].rstrip()
            self._pos += 1
        return None

    @staticmethod
    def _indent(line: str) -> int:
        return len(line) - len(line.lstrip())

    # ── Block mapping ─────────────────────────────────────────────────────────

    def _parse_block_mapping(self, indent: int) -> dict:
        result: dict[str, Any] = {}
        while True:
            line = self._peek()
            if line is None:
                break
            curr = self._indent(line)
            if curr < indent:
                break
            bare = line.lstrip()
            key, rest = _split_key(bare)
            if key is None:
                break
            self._pos += 1
            result[key] = self._resolve_value(rest, indent)
        return result

    # ── Block sequence ────────────────────────────────────────────────────────

    def _parse_block_sequence(self, indent: int) -> list:
        result: list[Any] = []
        while True:
            line = self._peek()
            if line is None:
                break
            curr = self._indent(line)
            if curr < indent:
                break
            bare = line.lstrip()
            if not (bare.startswith("- ") or bare == "-"):
                break
            self._pos += 1
            item_text = bare[2:].rstrip() if bare.startswith("- ") else ""
            if item_text:
                item_text = _strip_comment(item_text)
                # Detect inline map item: `- key: value`
                key, rest = _split_key(item_text)
                if key is not None and not item_text.startswith(("[", "{")):
                    sub: dict[str, Any] = {key: self._resolve_value(rest, indent + 2)}
                    sub.update(self._parse_block_mapping(indent + 2))
                    result.append(sub)
                else:
                    result.append(_parse_scalar(item_text))
            else:
                # Item content is on the next line(s).
                next_line = self._peek()
                if next_line is None:
                    result.append(None)
                else:
                    ni = self._indent(next_line)
                    if ni <= indent:
                        result.append(None)
                    else:
                        nb = next_line.lstrip()
                        if nb.startswith("- ") or nb == "-":
                            result.append(self._parse_block_sequence(ni))
                        else:
                            result.append(self._parse_block_mapping(ni))
        return result

    # ── Block scalar ( | and |- ) ─────────────────────────────────────────────

    def _parse_block_scalar(self, declaration_indent: int, strip: bool) -> str:
        """Parse a `|` block scalar.

        `declaration_indent` is the indent of the line bearing the `|` indicator;
        block content must be indented strictly more than that. If the first
        non-blank line is at indent <= declaration_indent, the block scalar is
        empty and that line is left for the parent parser to consume.
        """
        chunks: list[str] = []
        block_indent: int | None = None
        saved_pos = self._pos
        while self._pos < len(self._lines):
            raw = self._lines[self._pos]
            rstripped = raw.rstrip()
            if rstripped == "":
                chunks.append("")
                self._pos += 1
                continue
            curr = self._indent(rstripped)
            if curr <= declaration_indent:
                break
            if block_indent is None:
                block_indent = curr
            chunks.append(raw[block_indent:].rstrip())
            self._pos += 1
        if block_indent is None:
            # No indented content followed `|`. Rewind so the parent loop sees
            # the next sibling key (or blank line) instead of having it silently
            # consumed.
            self._pos = saved_pos
            return ""
        text = "\n".join(chunks)
        return text if strip else text + "\n"

    # ── Value resolver ────────────────────────────────────────────────────────

    def _resolve_value(self, rest: str, parent_indent: int) -> Any:
        rest = rest.rstrip()
        if rest in ("|", "|-", "|+"):
            strip = rest == "|-"
            return self._parse_block_scalar(parent_indent, strip)
        if rest == ">":
            raise ParseError(f"line {self._pos + 1}: folded scalars (>) not supported")
        if rest in ("&", "*") or rest.startswith("&") or rest.startswith("*"):
            raise ParseError(f"line {self._pos + 1}: anchors/aliases not supported")
        if rest == "":
            next_line = self._peek()
            if next_line is None:
                return None
            ni = self._indent(next_line)
            if ni <= parent_indent:
                return None
            nb = next_line.lstrip()
            if nb.startswith("- ") or nb == "-":
                return self._parse_block_sequence(ni)
            return self._parse_block_mapping(ni)
        return _parse_scalar(rest)


# ── Scalar parser ─────────────────────────────────────────────────────────────

def _parse_scalar(text: str) -> Any:
    text = text.strip()
    if not text or text in _NULL_SET:
        return None
    if text in _TRUE_SET:
        return True
    if text in _FALSE_SET:
        return False
    if _INT_RE.match(text):
        return int(text)
    if _DATE_RE.match(text):
        return text  # engine's _is_iso_date() accepts str; no datetime import needed
    if text.startswith("["):
        return _parse_flow_sequence(text)
    if text.startswith("{"):
        return _parse_flow_mapping(text)
    if text.startswith('"'):
        return _parse_double_quoted(text)
    if text.startswith("'"):
        return _parse_single_quoted(text)
    return text


def _parse_double_quoted(text: str) -> str:
    if not (text.startswith('"') and text.endswith('"') and len(text) >= 2):
        return text
    inner = text[1:-1]
    out: list[str] = []
    i = 0
    while i < len(inner):
        if inner[i] == "\\" and i + 1 < len(inner):
            esc = inner[i + 1]
            out.append({"n": "\n", "t": "\t", '"': '"', "\\": "\\"}.get(esc, esc))
            i += 2
        else:
            out.append(inner[i])
            i += 1
    return "".join(out)


def _parse_single_quoted(text: str) -> str:
    if not (text.startswith("'") and text.endswith("'") and len(text) >= 2):
        return text
    return text[1:-1].replace("''", "'")


def _parse_flow_sequence(text: str) -> list:
    if not (text.startswith("[") and text.endswith("]")):
        return [text]
    inner = text[1:-1].strip()
    if not inner:
        return []
    return [_parse_scalar(item.strip()) for item in _split_flow(inner)]


def _parse_flow_mapping(text: str) -> dict:
    if not (text.startswith("{") and text.endswith("}")):
        return {}
    inner = text[1:-1].strip()
    if not inner:
        return {}
    result: dict[str, Any] = {}
    for pair in _split_flow(inner):
        pair = pair.strip()
        key, _, val = pair.partition(": ")
        if _:
            k = key.strip()
            # Strip quotes from keys (YAML keys are sometimes double-quoted).
            if len(k) >= 2 and k[0] == k[-1] and k[0] in ('"', "'"):
                k = k[1:-1]
            result[k] = _parse_scalar(val.strip())
    return result


def _split_flow(text: str) -> list[str]:
    """Split comma-separated flow content, respecting nesting and quotes."""
    parts: list[str] = []
    depth = 0
    in_q: str | None = None
    buf: list[str] = []
    for c in text:
        if in_q:
            buf.append(c)
            if c == in_q:
                in_q = None
        elif c in ('"', "'"):
            in_q = c
            buf.append(c)
        elif c in ("[", "{"):
            depth += 1
            buf.append(c)
        elif c in ("]", "}"):
            depth -= 1
            buf.append(c)
        elif c == "," and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(c)
    if buf:
        parts.append("".join(buf))
    return parts


# ── Key splitter and comment stripper ─────────────────────────────────────────

def _split_key(bare: str) -> tuple[str | None, str]:
    """Split 'key: rest' → ('key', 'rest'). Returns (None, '') if not kv."""
    in_q: str | None = None
    for i, c in enumerate(bare):
        if in_q:
            if c == in_q:
                in_q = None
        elif c in ('"', "'"):
            in_q = c
        elif c == ":":
            if i + 1 < len(bare) and bare[i + 1] in (" ", "\t"):
                rest = bare[i + 2 :].lstrip()
                return bare[:i], _strip_comment(rest)
            if i + 1 == len(bare):
                return bare[:i], ""
    return None, ""


def _strip_comment(text: str) -> str:
    """Remove trailing `# comment` (or leading `#` comment) from a value."""
    if text.startswith("#"):
        return ""
    in_q: str | None = None
    for i, c in enumerate(text):
        if in_q:
            if c == in_q:
                in_q = None
        elif c in ('"', "'"):
            in_q = c
        elif c == "#" and i > 0 and text[i - 1] in (" ", "\t"):
            return text[:i].rstrip()
    return text
