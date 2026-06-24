"""Minimal YAML subset parser — round-trips goc card frontmatter with no deps.

Public API:
    safe_load(text: str) -> dict | list | None

Accepted YAML features (driven by what goc/engine.py emits and reads):
  - Top-level block mapping with simple string keys
  - Scalar values: null/~, bool (true/false/yes/no), integer, ISO date string,
    plain string, single-quoted string, double-quoted string (with \\ \\n escapes)
  - Inline flow list: [a, b, c]
  - Inline flow map: {k: v, k2: v2}
  - Block literal scalar: | (clip), |- (strip) and |+ (keep) chomping
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
# Literal block scalar header: `|`, with an optional explicit indentation
# indicator (`|2`) and an optional chomping indicator (`-` strip / `+` keep).
_BLOCK_INDICATOR_RE = re.compile(r"^\|(\d+)?([-+]?)$")
# Folded block scalar header: `>` with the same optional indent/chomp
# indicators. Folded scalars are unsupported and must raise — this regex
# catches every variant (`>-`, `>+`, `>2`, `>2-`, …), not just the bare `>`.
_FOLDED_INDICATOR_RE = re.compile(r"^>(\d+)?([-+]?)$")
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
        """Return first non-blank, non-comment line; advance past skipped lines.

        Every structurally-significant line (mapping keys, sequence items,
        value continuations) is fetched through here, while block-scalar
        content is read directly from ``self._lines``. So this is the one
        chokepoint at which indentation is structural — and the right place
        to enforce the docstring's "Tabs as indentation -> ParseError"
        contract without rejecting legitimate tabs inside literal blocks.
        """
        while self._pos < len(self._lines):
            line = self._lines[self._pos]
            bare = line.rstrip().lstrip()
            if bare and not bare.startswith("#"):
                lead = line[: len(line) - len(line.lstrip())]
                if "\t" in lead:
                    raise ParseError(
                        f"line {self._pos + 1}: tabs are not allowed as indentation"
                    )
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
            if curr > indent:
                # In every valid parse path the line at the top of this loop
                # is at <= indent: nested mappings/sequences/block scalars are
                # consumed in full by _resolve_value before control returns
                # here. A more-indented line is therefore malformed — an
                # over-indented key (silently promoted to a sibling) or a bare
                # plain-scalar continuation (which would otherwise truncate
                # every following key). Fail loud, matching the tab guard in
                # _peek and the ambiguous-indent guard in _parse_block_scalar.
                raise ParseError(
                    f"line {self._pos + 1}: line is indented {curr}, more than "
                    f"the surrounding mapping at {indent}; unexpected indentation"
                )
            bare = line.lstrip()
            key, rest = _split_key(bare)
            if key is None:
                # A line at the mapping indent that is not a recognizable
                # `key: value` entry — most commonly a missing space after the
                # colon (`status:open`), which YAML treats as a plain scalar,
                # not a key, but also a bare scalar with no colon at all. The
                # dedent (`curr < indent`) and over-indent (`curr > indent`)
                # cases are already handled above, so anything reaching here is
                # a malformed sibling entry. Silently breaking would drop this
                # line AND every key below it from the document — the exact
                # truncation the over-indent guard above and the tab guard in
                # _peek exist to prevent. Fail loud to match that posture.
                raise ParseError(
                    f"line {self._pos + 1}: {bare!r} is not a valid "
                    f"'key: value' mapping entry (a ':' key separator must be "
                    f"followed by a space); breaking here would silently drop "
                    f"it and every following key"
                )
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
            if curr > indent:
                # The mirror of the _parse_block_mapping guard: in every valid
                # parse path the line at the top of this loop is at <= indent.
                # A nested sequence's more-indented items are consumed in full
                # by the recursive _parse_block_sequence(ni) call below before
                # control returns here, so a more-indented `- item` line is
                # malformed — an over-indented item that would otherwise be
                # silently absorbed as a same-level sibling. Fail loud, matching
                # the mapping guard, the tab guard in _peek, and the
                # ambiguous-indent guard in _parse_block_scalar.
                raise ParseError(
                    f"line {self._pos + 1}: line is indented {curr}, more than "
                    f"the surrounding sequence at {indent}; unexpected indentation"
                )
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

    # ── Block scalar ( |, |- and |+ ) ─────────────────────────────────────────

    def _parse_block_scalar(
        self, declaration_indent: int, chomp: str, explicit_indent: int | None = None
    ) -> str:
        """Parse a `|` block scalar.

        `declaration_indent` is the indent of the line bearing the `|` indicator;
        block content must be indented strictly more than that. If the first
        non-blank line is at indent <= declaration_indent, the block scalar is
        empty and that line is left for the parent parser to consume.

        `chomp` is the YAML chomping mode: "clip" (bare `|`, keep one trailing
        newline, drop trailing blank lines), "strip" (`|-`, no trailing newline)
        or "keep" (`|+`, preserve every trailing blank line).

        `explicit_indent` is the optional YAML indentation indicator (the `2` in
        `|2`): the block indent is then pinned to `declaration_indent +
        explicit_indent` instead of being inferred from the first content line.
        This lets a content line carry its own leading whitespace without the
        auto-inference folding it into the block indent (silent strip) or
        raising on a later, less-indented line (ambiguity). The emitter uses it
        whenever the first content line begins with whitespace.
        """
        chunks: list[str] = []
        block_indent: int | None = (
            None if explicit_indent is None else declaration_indent + explicit_indent
        )
        content_seen = False
        saved_pos = self._pos
        while self._pos < len(self._lines):
            raw = self._lines[self._pos]
            rstripped = raw.rstrip()
            if rstripped == "":
                # A line with nothing past rstrip() is either a structural
                # blank or a whitespace-only content line. Before the block
                # indent is fixed there is nothing to slice against, so treat
                # it as a structural blank. Once block_indent is known, slice
                # it like any content line: interior whitespace past the block
                # indent is meaningful and must survive the emit->parse round
                # trip (raw[block_indent:] yields the interior spaces, or ""
                # for a line shorter than the block indent — a genuine blank,
                # which the trailing-blank chomp below still drops).
                chunks.append("" if block_indent is None else raw[block_indent:])
                self._pos += 1
                continue
            curr = self._indent(rstripped)
            if curr <= declaration_indent:
                break
            if block_indent is None:
                block_indent = curr
            elif curr < block_indent:
                # A content line less-indented than the block's established
                # indent cannot belong to the block (YAML fixes block indent
                # from the first non-empty line). It is also over-indented
                # relative to the declaration's parent, so it is not a clean
                # sibling either — slicing it with raw[block_indent:] would eat
                # real characters. Reject rather than silently corrupt.
                raise ParseError(
                    f"line {self._pos + 1}: block scalar content line is "
                    f"indented {curr}, less than the block indent "
                    f"{block_indent} but more than its declaration "
                    f"{declaration_indent}; ambiguous indentation"
                )
            # Strip only the leading block indentation; trailing whitespace on a
            # content line is meaningful in a YAML literal block (e.g. a Markdown
            # hard-break) and must survive the emit->parse round-trip.
            chunks.append(raw[block_indent:])
            content_seen = True
            self._pos += 1
        if not content_seen:
            # No indented content followed `|`. Rewind so the parent loop sees
            # the next sibling key (or blank line) instead of having it silently
            # consumed. (With an explicit indicator block_indent is preset, so we
            # gate the rewind on whether a real content line was actually read.)
            self._pos = saved_pos
            return ""
        if chomp == "keep":
            # Preserve every trailing blank line plus the final line break.
            return "\n".join(chunks) + "\n"
        # clip and strip both drop trailing blank lines; they differ only in
        # whether the single final line break survives.
        end = len(chunks)
        while end > 0 and chunks[end - 1] == "":
            end -= 1
        text = "\n".join(chunks[:end])
        return text if chomp == "strip" else text + "\n"

    # ── Value resolver ────────────────────────────────────────────────────────

    def _resolve_value(self, rest: str, parent_indent: int) -> Any:
        rest = rest.rstrip()
        block_m = _BLOCK_INDICATOR_RE.match(rest)
        if block_m:
            explicit_indent = int(block_m.group(1)) if block_m.group(1) else None
            chomp = {"": "clip", "-": "strip", "+": "keep"}[block_m.group(2)]
            return self._parse_block_scalar(
                parent_indent, chomp, explicit_indent=explicit_indent
            )
        if _FOLDED_INDICATOR_RE.match(rest):
            raise ParseError(f"line {self._pos + 1}: folded scalars (>) not supported")
        if rest in ("&", "*") or rest.startswith("&") or rest.startswith("*"):
            raise ParseError(f"line {self._pos + 1}: anchors/aliases not supported")
        if rest == "":
            next_line = self._peek()
            if next_line is None:
                return None
            ni = self._indent(next_line)
            nb = next_line.lstrip()
            is_seq = nb.startswith("- ") or nb == "-"
            # A block sequence's items may sit at the SAME indent as the
            # parent key (valid YAML, and what PyYAML emits). A mapping
            # continuation must stay strictly more indented, otherwise a
            # sibling key would be swallowed as a nested mapping.
            if is_seq and ni >= parent_indent:
                return self._parse_block_sequence(ni)
            if not is_seq and ni > parent_indent:
                return self._parse_block_mapping(ni)
            return None
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
        key, sep, val = pair.partition(":")
        if sep:
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
    escaped = False
    for c in text:
        if escaped:
            buf.append(c)
            escaped = False
        elif in_q:
            buf.append(c)
            if c == "\\" and in_q == '"':
                escaped = True  # double-quoted YAML escapes the next char
            elif c == in_q:
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
    escaped = False
    for i, c in enumerate(bare):
        if escaped:
            escaped = False
        elif in_q:
            if c == "\\" and in_q == '"':
                escaped = True  # double-quoted YAML escapes the next char
            elif c == in_q:
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
    # Quote-tracking only applies to a genuinely *quoted* scalar (one that
    # starts with a quote) or to the interior of an inline flow collection
    # (`[...]`/`{...}`). In a bare value a lone quote char — the apostrophe in
    # `don't`, the `'` in `5 o'clock` — is ordinary content and must not flip
    # into quote mode, or it would suppress comment detection for the rest of
    # the line. A flow collection, by contrast, uses quotes to delimit its
    # elements, so a `#` inside a quoted element is content, not a comment;
    # bracket depth gates comment detection so only a `#` outside both quotes
    # and brackets terminates the value.
    flow = text[:1] in ("[", "{")
    quoted = text[:1] in ('"', "'")
    in_q: str | None = None
    escaped = False
    depth = 0
    for i, c in enumerate(text):
        if escaped:
            escaped = False
        elif in_q:
            if c == "\\" and in_q == '"':
                escaped = True  # double-quoted YAML escapes the next char
            elif c == in_q:
                in_q = None
        elif flow and c in ("[", "{"):
            depth += 1
        elif flow and c in ("]", "}"):
            if depth > 0:
                depth -= 1
        elif (quoted or flow) and c in ('"', "'"):
            in_q = c
        elif c == "#" and depth == 0 and i > 0 and text[i - 1] in (" ", "\t"):
            return text[:i].rstrip()
    return text
