"""Draw the animated SVGs used in the README.

GitHub shows SVG images but runs no script in them, so every animation here is CSS
keyframes or SMIL. Each piece of a sequence shares one loop length and gets its own
keyframe percentages, which is what lets the whole sequence repeat together.

Figures come from eval/results, so the art cannot drift from the measured numbers.

    python -m scripts.readme_art
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "assets"

INK = "#0a0a0a"
MUTED = "#686c73"
TILE = "#f7f6f3"
TILE2 = "#eeede9"
LINE = "#e7e5e0"
OK = "#22a06b"
BAD = "#ef4444"
WARN = "#f59e0b"
FONT = "'Geist','Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
MONO = "'Geist Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"


def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def appear(name: str, start: float, end: float = 0.94, dy: int = 8) -> str:
    """Keyframes: hidden until `start`, slide in, stay until `end`, fade out by 100%."""
    s, e = start * 100, end * 100
    return (
        f"@keyframes {name}{{0%,{s:.1f}%{{opacity:0;transform:translateY({dy}px)}}"
        f"{s + 3:.1f}%,{e:.1f}%{{opacity:1;transform:none}}"
        f"100%{{opacity:0;transform:none}}}}"
        f".{name}{{animation:{name} var(--loop) cubic-bezier(.2,.7,.2,1) infinite;opacity:0}}"
    )


def svg(width: int, height: int, loop: float, css: str, body: str, label: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{esc(label)}">'
        f"<style>:root{{--loop:{loop}s}}svg{{--loop:{loop}s}}"
        f"text{{font-family:{FONT};fill:{INK}}}.m{{fill:{MUTED}}}.mono{{font-family:{MONO}}}"
        f"{css}"
        "@media (prefers-reduced-motion:reduce){*{animation:none!important;opacity:1!important}}"
        f"</style>{body}</svg>"
    )


def load(name: str) -> dict:
    return json.loads((ROOT / "eval" / "results" / name).read_text(encoding="utf-8"))


def hero() -> str:
    loop = 9.0
    css = [
        appear("a0", 0.02, dy=12),
        appear("a1", 0.06, dy=12),
        appear("a2", 0.10, dy=12),
        appear("card", 0.14, dy=16),
    ]
    rows = [
        (
            "Matches the order and delivery",
            "Billed 144.94 units, only 119 delivered",
            BAD,
            "Problem",
        ),
        ("Price is normal for this supplier", "In line with past prices", OK, "Passed"),
        ("Not a duplicate", "First time we have seen it", OK, "Passed"),
        ("VAT adds up", "Recalculated to the paisa", OK, "Passed"),
    ]
    row_svg = []
    for i, (name, says, colour, word) in enumerate(rows):
        cls = f"r{i}"
        css.append(appear(cls, 0.24 + i * 0.07, dy=6))
        y = 136 + i * 50
        row_svg.append(
            f'<g class="{cls}"><circle cx="672" cy="{y + 4}" r="5" fill="{colour}"/>'
            f'<text x="690" y="{y + 9}" font-size="15" font-weight="500">{esc(name)}</text>'
            f'<text x="690" y="{y + 29}" font-size="13" class="m">{esc(says)}</text>'
            f'<text x="1110" y="{y + 9}" font-size="13" text-anchor="end" class="m">{word}</text></g>'
        )
        if i < len(rows) - 1:
            row_svg.append(
                f'<line class="{cls}" x1="690" x2="1110" y1="{y + 40}" y2="{y + 40}" stroke="{LINE}"/>'
            )
    css.append(appear("next", 0.56, dy=10))
    css.append(
        "@keyframes stamp{0%,66%{opacity:0;transform:scale(1.6) rotate(-14deg)}"
        "70%,94%{opacity:1;transform:scale(1) rotate(-8deg)}100%{opacity:0}}"
        ".stamp{animation:stamp var(--loop) cubic-bezier(.2,.9,.3,1.3) infinite;opacity:0;"
        "transform-box:fill-box;transform-origin:center}"
    )
    body = f"""
<rect x="0.5" y="0.5" width="1199" height="439" rx="28" fill="#fff" stroke="{LINE}"/>
<g class="a0"><circle cx="92" cy="118" r="30" fill="{INK}"/>
<path d="M78 118l10 10 18-20" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/></g>
<text class="a1" x="60" y="222" font-size="60" font-weight="600" letter-spacing="-2.4">Countersign</text>
<text class="a2 m" x="62" y="266" font-size="21">Check every supplier invoice before you pay.</text>
<g class="a2">
<rect x="60" y="310" width="176" height="44" rx="22" fill="{INK}"/>
<text x="148" y="338" font-size="15" font-weight="500" text-anchor="middle" fill="#fff" style="fill:#fff">Live demo</text>
<rect x="248" y="310" width="176" height="44" rx="22" fill="{TILE2}"/>
<text x="336" y="338" font-size="15" font-weight="500" text-anchor="middle">MIT · open source</text>
</g>
<g class="card">
<rect x="640" y="40" width="500" height="360" rx="22" fill="{TILE}"/>
<text x="664" y="80" font-size="12" class="mono m" fill="{MUTED}">INVOICE HAL-2508-0011</text>
<text x="664" y="110" font-size="21" font-weight="500" letter-spacing="-0.4">Halda Steel Trading Ltd</text>
<text x="1116" y="110" font-size="17" font-weight="500" text-anchor="end">BDT 20,167,167.39</text>
</g>
{"".join(row_svg)}
<g class="next">
<rect x="664" y="334" width="452" height="46" rx="16" fill="{INK}"/>
<text x="684" y="362" font-size="14.5" font-weight="500" style="fill:#fff">Suggested: hold it and ask for proof of delivery</text>
</g>
<g class="stamp">
<circle cx="612" cy="332" r="44" fill="none" stroke="{BAD}" stroke-width="3"/>
<circle cx="612" cy="332" r="37" fill="none" stroke="{BAD}" stroke-width="1.2"/>
<text x="612" y="329" font-size="13" font-weight="700" text-anchor="middle" style="fill:{BAD}" letter-spacing="1.5">ON HOLD</text>
<text x="612" y="346" font-size="9" text-anchor="middle" style="fill:{BAD}" letter-spacing="1">ASK FOR PROOF</text>
</g>
"""
    return svg(
        1200,
        440,
        loop,
        "".join(css),
        body,
        "Countersign checks an invoice: one problem found, put on hold",
    )


def pipeline() -> str:
    loop = 7.0
    nodes = [
        ("PDF · XLSX · CSV", "arrives"),
        ("Read", "copy fields as printed"),
        ("Validate", "sums must add up"),
        ("4 checks", "order · price · duplicate · VAT"),
        ("Suggest", "next step, with sources"),
        ("A person signs", "nothing pays itself"),
    ]
    width, gap, top = 170, 26, 70
    total = len(nodes) * width + (len(nodes) - 1) * gap
    left = (1200 - total) / 2
    css, parts = [], []
    for i, (title, sub) in enumerate(nodes):
        x = left + i * (width + gap)
        on = 0.08 + i * 0.13
        last = i == len(nodes) - 1
        css.append(
            f"@keyframes n{i}{{0%,{on * 100:.1f}%{{fill:{TILE}}}{on * 100 + 4:.1f}%,94%{{fill:{INK}}}100%{{fill:{TILE}}}}}"
            f".n{i}{{animation:n{i} var(--loop) ease infinite}}"
            f"@keyframes t{i}{{0%,{on * 100:.1f}%{{fill:{INK}}}{on * 100 + 4:.1f}%,94%{{fill:#fff}}100%{{fill:{INK}}}}}"
            f".t{i}{{animation:t{i} var(--loop) ease infinite}}"
        )
        parts.append(
            f'<rect class="n{i}" x="{x}" y="{top}" width="{width}" height="56" rx="28" fill="{TILE}"/>'
            f'<text class="t{i}" x="{x + width / 2}" y="{top + 34}" font-size="16" font-weight="500" '
            f'text-anchor="middle">{esc(title)}</text>'
            f'<text x="{x + width / 2}" y="{top + 84}" font-size="12.5" text-anchor="middle" class="m">{esc(sub)}</text>'
        )
        if not last:
            x2 = x + width
            parts.append(
                f'<path d="M{x2 + 4} {top + 28} h{gap - 8}" stroke="{MUTED}" stroke-width="1.5"/>'
                f'<path d="M{x2 + gap - 9} {top + 23} l5 5 -5 5" fill="none" stroke="{MUTED}" stroke-width="1.5"/>'
            )
    read_x = left + (width + gap) + width / 2
    val_x = left + 2 * (width + gap) + width / 2
    chk_x = left + 3 * (width + gap) + width / 2
    q_y = 200
    parts.append(
        f'<path d="M{read_x} {top + 96} V{q_y} H{chk_x}" fill="none" stroke="{LINE}" stroke-width="1.5" stroke-dasharray="4 5"/>'
        f'<path d="M{val_x} {top + 96} V{q_y}" fill="none" stroke="{LINE}" stroke-width="1.5" stroke-dasharray="4 5"/>'
        f'<rect x="{chk_x - 10}" y="{q_y - 20}" width="220" height="40" rx="20" fill="#fff" stroke="{LINE}"/>'
        f'<circle cx="{chk_x + 10}" cy="{q_y}" r="5" fill="{WARN}"/>'
        f'<text x="{chk_x + 24}" y="{q_y + 5}" font-size="13.5">Unsure or unreadable → a person</text>'
    )
    start_x = left + 20
    end_x = left + total - 20
    parts.append(
        f'<circle r="6" fill="{OK}" stroke="#fff" stroke-width="2">'
        f'<animateMotion dur="{loop}s" repeatCount="indefinite" keyPoints="0;0;1;1" keyTimes="0;0.06;0.8;1" calcMode="linear" '
        f'path="M{start_x} {top - 14} H{end_x}"/></circle>'
    )
    body = (
        f'<rect x="0.5" y="0.5" width="1199" height="239" rx="28" fill="#fff" stroke="{LINE}"/>'
        + "".join(parts)
    )
    return svg(
        1200,
        240,
        loop,
        "".join(css),
        body,
        "Pipeline: arrives, read, validate, four checks, suggest, a person signs",
    )


def metrics() -> str:
    checks = load("checks-current.json")
    before = load("checks-without-materiality-floor.json")
    extraction = load("extraction.json")
    planted = checks["defects"]["planted"]
    caught = planted - checks["defects"]["reached_cleared"]
    fp = checks["clean_invoices"]["false_positive_rate"] * 100
    fp_before = before["clean_invoices"]["false_positive_rate"] * 100
    auto = checks["routing"]["cleared_share"] * 100
    wrong_v1 = extraction["v1_reader_only"]["persisted_wrong"]
    wrong_v2 = extraction["v2_reader_plus_validators"].get("persisted_wrong", 0)
    loop = 8.0
    figures = [
        (f"{caught}/{planted}", "planted mistakes caught"),
        (f"{fp:.1f}%", f"false alarms (was {fp_before:.1f}%)"),
        (f"{auto:.1f}%", "passed with no investigation"),
        (f"{wrong_v1} → {wrong_v2}", "misread invoices stored"),
    ]
    css, parts = [], []
    for i, (value, label) in enumerate(figures):
        x = 60 + i * 280
        css.append(appear(f"f{i}", 0.03 + i * 0.05, dy=14))
        parts.append(
            f'<g class="f{i}"><line x1="{x}" x2="{x + 250}" y1="52" y2="52" stroke="{LINE}"/>'
            f'<text x="{x}" y="112" font-size="50" font-weight="500" letter-spacing="-2">{esc(value)}</text>'
            f'<text x="{x}" y="140" font-size="14.5" class="m">{esc(label)}</text></g>'
        )
    names = {
        "THREE_WAY_MATCH": "Matches the order and delivery",
        "PRICE_VARIANCE": "Price is normal for this supplier",
        "DUPLICATE_INVOICE": "Not a duplicate",
        "TAX_ARITHMETIC": "VAT adds up",
    }
    parts.append(
        '<text x="60" y="208" font-size="15" font-weight="500">Each check, on the mistakes planted for it</text>'
    )
    bar_x, bar_w = 360, 640
    for i, (code, name) in enumerate(names.items()):
        recall = checks["per_check"][code]["recall_strict"]
        owned = checks["per_check"][code]["defects_it_owns"]
        y = 240 + i * 42
        grow = 0.30 + i * 0.05
        css.append(
            f"@keyframes b{i}{{0%,{grow * 100:.1f}%{{transform:scaleX(0)}}{grow * 100 + 12:.1f}%,94%{{transform:scaleX(1)}}100%{{transform:scaleX(0)}}}}"
            f".b{i}{{animation:b{i} var(--loop) cubic-bezier(.2,.7,.2,1) infinite;transform-box:fill-box;transform-origin:left}}"
        )
        css.append(appear(f"v{i}", grow + 0.1, dy=0))
        parts.append(
            f'<text x="60" y="{y + 5}" font-size="14">{esc(name)}</text>'
            f'<rect x="{bar_x}" y="{y - 5}" width="{bar_w}" height="12" rx="6" fill="{TILE2}"/>'
            f'<rect class="b{i}" x="{bar_x}" y="{y - 5}" width="{bar_w * recall:.1f}" height="12" rx="6" fill="{INK}"/>'
            f'<text class="v{i}" x="1140" y="{y + 5}" font-size="14" text-anchor="end">{recall * 100:.1f}% of {owned}</text>'
        )
    body = (
        f'<rect x="0.5" y="0.5" width="1199" height="419" rx="28" fill="#fff" stroke="{LINE}"/>'
        + "".join(parts)
    )
    return svg(
        1200,
        420,
        loop,
        "".join(css),
        body,
        f"{caught} of {planted} planted mistakes caught, {fp:.1f}% false alarms",
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, draw in (("hero", hero), ("pipeline", pipeline), ("metrics", metrics)):
        (OUT / f"{name}.svg").write_text(draw(), encoding="utf-8")
        print(f"wrote docs/assets/{name}.svg")


if __name__ == "__main__":
    main()
