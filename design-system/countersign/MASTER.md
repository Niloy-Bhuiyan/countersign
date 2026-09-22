# Design System Master File

> When building a specific page, first check `design-system/countersign/pages/[page-name].md`.
> If that file exists, its rules override this file. Otherwise follow the rules below.

**Project:** Countersign
**Style:** Minimalism & Swiss (monochrome, whitespace, grid, essential elements only)
**Replaces:** the 2026-09-22 trust-blue SaaS palette, which users found busy and hard to read.

## Principles

1. **One colour, black.** Ink on white. Every primary action is a black pill.
2. **Colour only means status.** A small dot (green, amber, red, blue) always sits next to a word, never alone.
3. **Say it once, briefly.** Titles over paragraphs. Detail lives behind "Details", "Why" or an ⓘ tip.
4. **Tiles, not boxes.** Warm grey tiles with a 24px radius. No borders, no shadows (the hero window is the one exception).
5. **Show the product.** The home page leads with a live preview of the review screen, not a description of it.

## Tokens

| Role | Value | Variable |
|------|-------|----------|
| Page | `#FFFFFF` | `--bg` |
| Tile | `#F7F6F3` | `--tile` |
| Secondary button / pressed | `#EEEDE9` | `--tile-2` |
| Hover | `#E4E2DD` | `--tile-3` |
| Hairline | `#E7E5E0` | `--line` |
| Ink | `#0A0A0A` | `--fg` |
| Body secondary | `#3D4046` | `--fg-2` |
| Muted (≥ 4.5:1 on white and on tile) | `#686C73` | `--fg-3` |
| Status dots | `#22A06B` ok · `#F59E0B` warn · `#EF4444` bad · `#3B82F6` info · `#A3A3A3` muted | `--*-dot` |

Radius: tiles 24px, inner blocks 16px, inputs and buttons fully rounded.

## Typography

- **Geist** for everything, **Geist Mono** for invoice and order numbers.
- Weight 500 for headings, 400 for body. Tight tracking on large sizes.
- Hero 64/1.02 (−0.045em) · page title 44 · section title 36 · card title 17 · body 15/1.6 · muted lead 17–18.
- Money uses tabular figures. Currency is written "BDT" (Geist has no ৳ glyph).

## Components

- **Buttons:** pill, 44px min height. `btn-primary` black; `btn` grey; `btn-ghost` transparent.
- **Chips:** outlined pills; the selected one turns black. Used to choose a mistake in the lab.
- **Status pill:** white pill with a coloured dot and a word.
- **Tip:** ⓘ button that opens a black note on click or focus and closes on Escape.
- **Guide:** a one-line black bar on first visit to Review, with Skip and Next.
- **Suggested next step:** black bar inside the summary tile; "Why" expands the reasoning.

## Anti-patterns

- Gradients, drop shadows on cards, coloured backgrounds for status.
- Paragraph explanations under every heading.
- Icons as decoration; an icon appears only when it adds meaning.
- Colour without a word next to it.

## Pre-delivery checklist

- [ ] Text contrast ≥ 4.5:1 (muted text is `#686C73`, not lighter)
- [ ] Visible focus ring (2px ink outline)
- [ ] Touch targets ≥ 44px for primary actions
- [ ] No horizontal scroll at 375px
- [ ] `prefers-reduced-motion` respected

## Signature

What makes Countersign recognisable on top of the monochrome base. All of it lives in
`web/components/motion.tsx` and the "signature" block at the end of `globals.css`.

- **The stamp.** A worn-ink rubber stamp with COUNTERSIGN around the rim. It lands when a decision
  is signed (APPROVED green, ON HOLD amber, ESCALATED red) and on a lab verdict (CAUGHT or PASSED,
  in white on the black bar). It is decorative: the same status is always written nearby.
- **The pen stroke.** A handwritten line that signs "pay" in the headline.
- **Self-drawing ticks.** The logo, the headline mark and the large circle draw their tick.
- **Reading and running.** The home preview sweeps a scan line and raises findings in turn; an
  invoice's four check dots light up one after another.
- **Counting.** Home figures count up once they are seen.

Every animated element's resting style is its final state, and keyframes only describe the way in,
so reduced motion shows the finished page. Motion never delays an action or hides information.
