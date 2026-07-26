"""Show that `## Decision required` option lists have no machine-readable shape.

Walks every gated card's `## Decision required` section and classifies how its
options are authored. Exits non-zero while several mutually incompatible shapes
coexist with no declared contract, and demonstrates one concrete misparse: a
reader that resolves H3 headings as options reports the wrong option count for a
card whose sub-decisions nest their own lists.

Run: uv run python .game-of-cards/deck/<this-card>/reproduce.py
"""
import re
import sys
from collections import Counter
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


ROOT = _repo_root()
sys.path.insert(0, str(ROOT))
DECK = ROOT / ".game-of-cards" / "deck"

FENCE = re.compile(r"^(\s*)(`{3,}|~{3,})")
H3 = re.compile(r"^###\s+(?P<label>.+?)\s*$", re.M)
BOLD_OPT = re.compile(r"^\*\*Option\s+[A-Z0-9]+[^*]*?\*\*", re.M)
NUM_BOLD = re.compile(r"^\s*(?:\d+\.|[-*])\s+\*\*(?P<label>.+?)\*\*", re.M)
PC_LEAD = re.compile(r"^\**\s*(Pros?|Cons?|Trade-?offs?|Risk)\b", re.I)
META_H3 = re.compile(r"^(Recommendation|Recommended|Fix sketch|Note|Sibling|"
                     r"Cross-ref|Empirical|Why|Scope|What|Location|Decision)\b", re.I)


def mask_fences(text: str) -> str:
    """Blank fenced-block lines, preserving offsets."""
    out, fence = [], None
    for line in text.split("\n"):
        m = FENCE.match(line)
        if fence is None and m:
            fence = m.group(2)[0] * 3
            out.append(" " * len(line))
            continue
        if fence is not None:
            out.append(" " * len(line))
            if line.strip().startswith(fence):
                fence = None
            continue
        out.append(line)
    return "\n".join(out)


def decision_section(readme: Path):
    parts = readme.read_text(encoding="utf-8").split("---", 2)
    body = parts[2] if len(parts) > 2 else parts[0]
    masked = mask_fences(body)
    m = re.search(r"^##\s+Decision required\b.*$", masked, re.M)
    if not m:
        return None
    nxt = re.search(r"^## ", masked[m.end():], re.M)
    return body[m.start(): m.end() + nxt.start()] if nxt else body[m.start():]


def gated_titles():
    """Cards whose frontmatter raises a human gate."""
    for readme in sorted(DECK.glob("*/README.md")):
        head = readme.read_text(encoding="utf-8").split("---", 2)
        fm = head[1] if len(head) > 2 else ""
        gate = re.search(r"^human_gate:\s*(\w+)", fm, re.M)
        if gate and gate.group(1) in ("decision", "session"):
            yield readme


def classify(sec: str):
    """Return (shape, option_count) as an independent reader would see it."""
    masked = mask_fences(sec)
    heads = [h for h in H3.finditer(masked) if not META_H3.match(h.group("label"))]
    if len(heads) >= 2:
        if all(re.match(r"^Option\s", h.group("label"), re.I) for h in heads):
            return "h3-option-headings", len(heads)
        return "h3-subsections", len(heads)
    if len(BOLD_OPT.findall(sec)) >= 2:
        return "bold-run-option-paragraphs", len(BOLD_OPT.findall(sec))
    items = [m for m in NUM_BOLD.finditer(sec) if not PC_LEAD.match(m.group("label"))]
    if len(items) >= 2:
        return "numbered-bold-list", len(items)
    return "no-parseable-list", 0


def main() -> int:
    shapes, pc_spellings = Counter(), Counter()
    total = 0
    nested_misparse = []

    for readme in gated_titles():
        sec = decision_section(readme)
        if sec is None:
            continue
        total += 1
        shape, n = classify(sec)
        shapes[shape] += 1

        for m in re.finditer(r"^\s*(?:[-*]\s*)?(\**(?:Pros?|Cons?|Trade-?offs?|Risk)\**\s*[:—–-]?)",
                             sec, re.M | re.I):
            pc_spellings[m.group(1).strip()] += 1

        # A sub-decision H3 whose body carries its own option list: the H3 reader
        # counts the headings, but the card's real options are the nested items.
        if shape == "h3-subsections":
            masked = mask_fences(sec)
            heads = [h for h in H3.finditer(masked) if not META_H3.match(h.group("label"))]
            bounds = [h.start() for h in heads] + [len(sec)]
            for i, h in enumerate(heads):
                block = sec[h.end(): bounds[i + 1]]
                inner = [m for m in NUM_BOLD.finditer(block)
                         if not PC_LEAD.match(m.group("label"))]
                if len(inner) >= 2:
                    nested_misparse.append(
                        (readme.parent.name, h.group("label").strip(), n, len(inner)))

    print(f"gated cards with a '## Decision required' section : {total}")
    print("\nauthored option shapes found (all in one deck):")
    for shape, n in shapes.most_common():
        print(f"  {n:>4}  {shape}")

    print(f"\ndistinct Pro/Con marker spellings: {len(pc_spellings)}")
    for spelling, n in pc_spellings.most_common(8):
        print(f"  {n:>4}  {spelling!r}")

    if nested_misparse:
        print("\nconcrete misparse — H3 reader vs the card's real option list:")
        for slug, head, outer, inner in nested_misparse:
            print(f"  {slug}")
            print(f"     sub-decision {head!r}")
            print(f"     H3 reader sees {outer} option(s); the card offers {inner}")

    selectable = {k: v for k, v in shapes.items() if k != "no-parseable-list"}
    print(f"\nVERDICT: {len(selectable)} mutually incompatible option shapes carry "
          f"selectable choices;")
    print(f"         {shapes['no-parseable-list']} gated cards expose no parseable list at all.")
    print("         No schema field, validator, or shared parser declares which is canonical,")
    print("         so every reader hand-rolls its own and drifts.")

    if len(selectable) > 1 or nested_misparse:
        print("\nreproduce: FAIL (defect stands)")
        return 1
    print("\nreproduce: PASS (a single declared shape is enforced)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
