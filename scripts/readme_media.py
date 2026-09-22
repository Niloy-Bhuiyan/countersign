"""Capture the README screenshots and GIFs from the live console.

Drives the locally installed Chrome with Playwright, so nothing is downloaded but the
Python package:

    pip install playwright pillow
    python -m scripts.readme_media [base-url]

The lab capture creates one real test invoice in a fresh workspace on the target site.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

from PIL import Image
from playwright.sync_api import Page, sync_playwright

OUT = Path(__file__).resolve().parents[1] / "docs" / "assets"
BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "https://countersign-zeta.vercel.app"
SKIP_TOUR = "try { localStorage.setItem('countersign.tour.review', 'done') } catch (e) {}"


def shot(page: Page, clip: dict | None = None) -> Image.Image:
    return Image.open(io.BytesIO(page.screenshot(clip=clip))).convert("RGB")


def save_png(image: Image.Image, name: str, width: int = 1280) -> None:
    if image.width > width:
        image = image.resize((width, round(image.height * width / image.width)), Image.LANCZOS)
    image.save(OUT / name, optimize=True)
    print(f"wrote docs/assets/{name} ({(OUT / name).stat().st_size // 1024} KB)")


def save_gif(
    frames: list[tuple[Image.Image, int]], name: str, width: int = 960, fade: int = 4
) -> None:
    """Frames are (image, hold in ms). Adds a short cross-fade between consecutive frames."""
    sized = []
    for image, hold in frames:
        if image.width != width:
            image = image.resize((width, round(image.height * width / image.width)), Image.LANCZOS)
        sized.append((image, hold))
    out, durations = [], []
    for i, (image, hold) in enumerate(sized):
        out.append(image)
        durations.append(hold)
        following = sized[(i + 1) % len(sized)][0]
        if following.size == image.size:
            for step in range(1, fade + 1):
                out.append(Image.blend(image, following, step / (fade + 1)))
                durations.append(40)
    palette = [
        frame.quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        for frame in out
    ]
    palette[0].save(
        OUT / name,
        save_all=True,
        append_images=palette[1:],
        duration=durations,
        loop=0,
        optimize=True,
        disposal=1,
    )
    print(f"wrote docs/assets/{name} ({(OUT / name).stat().st_size // 1024} KB, {len(out)} frames)")


def box(page: Page, selector: str, pad: int = 0) -> dict:
    b = page.locator(selector).first.bounding_box()
    assert b, selector
    return {
        "x": max(b["x"] - pad, 0),
        "y": max(b["y"] - pad, 0),
        "width": b["width"] + 2 * pad,
        "height": b["height"] + 2 * pad,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        desk = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
        desk.add_init_script(SKIP_TOUR)
        page = desk.new_page()

        # Home, first screen.
        page.goto(f"{BASE}/", wait_until="networkidle")
        page.wait_for_selector(".window .w-item")
        page.wait_for_timeout(800)
        save_png(shot(page), "home.png")

        # The live preview on the home page, clicking through each invoice.
        page.locator(".window").scroll_into_view_if_needed()
        page.evaluate("window.scrollBy(0, -40)")
        page.wait_for_timeout(400)
        frames = []
        items = page.locator(".window .w-item")
        for i in range(items.count()):
            items.nth(i).click()
            page.wait_for_timeout(900)
            frames.append((shot(page, box(page, ".window", 12)), 1700))
        save_gif(frames, "preview.gif")

        # Review with a VAT problem open.
        page.goto(f"{BASE}/review/?id=INV-0240", wait_until="networkidle")
        page.wait_for_selector(".summary")
        page.wait_for_timeout(800)
        save_png(shot(page), "review.png")

        # The lab: pick a mistake, create it, and get the verdict.
        page.goto(f"{BASE}/lab/?t=price_above_order", wait_until="networkidle")
        page.wait_for_selector(".lab .chip")
        page.wait_for_function("document.querySelector('.lab select')?.options.length > 0")
        page.wait_for_timeout(600)
        lab = lambda: shot(page, box(page, ".lab", 16))  # noqa: E731
        frames = [(lab(), 1400)]
        for chip in ("Get the VAT wrong", "Charge more than agreed"):
            page.get_by_role("button", name=chip, exact=True).click()
            page.wait_for_timeout(300)
            frames.append((lab(), 900))
        page.get_by_role("button", name="Create and check").click()
        page.wait_for_timeout(250)
        frames.append((lab(), 700))
        page.wait_for_selector(".lab-result .callout", timeout=60_000)
        page.wait_for_timeout(500)
        frames.append((lab(), 3200))
        save_gif(frames, "lab.gif")
        save_png(frames[-1][0], "lab.png")

        # Phone.
        phone = browser.new_context(
            viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True
        )
        phone.add_init_script(SKIP_TOUR)
        mobile = phone.new_page()
        mobile.goto(f"{BASE}/review/?id=INV-0240", wait_until="networkidle")
        mobile.wait_for_selector(".summary")
        mobile.locator(".detail-head").scroll_into_view_if_needed()
        mobile.wait_for_timeout(600)
        save_png(shot(mobile), "mobile.png", width=390)

        browser.close()


if __name__ == "__main__":
    main()
