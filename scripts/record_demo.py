"""Record the README demo GIF by driving the running Streamlit app with Playwright.

Prerequisites: the demo stack is running (run_vllm.sh / run_backend.sh / run_streamlit.sh).
Usage: uv run python scripts/record_demo.py [--url http://localhost:8501] [--out docs/images/demo.gif]

Each captured frame gets a caption banner (step number, title, explanation); ffmpeg turns the
annotated frames into a palette-optimised GIF.
"""

import argparse
import io
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import Frame, Page, sync_playwright

VIEWPORT = {"width": 1440, "height": 900}
OUT_WIDTH = 960
FPS = 5
FONT_REGULAR = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FONT_BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
BANNER_HEIGHT = 92
RESULT_TIMEOUT_MS = 90_000


@dataclass
class Caption:
    step: int
    title: str
    body: str


@dataclass
class Recorder:
    page: Page
    total_steps: int
    frames: list[tuple[bytes, Caption]] = field(default_factory=list)

    def capture(self, seconds: float, caption: Caption) -> None:
        for _ in range(max(1, round(seconds * FPS))):
            start = time.perf_counter()
            self.frames.append((self.page.screenshot(), caption))
            time.sleep(max(0.0, 1 / FPS - (time.perf_counter() - start)))

    def capture_once(self, caption: Caption) -> None:
        self.frames.append((self.page.screenshot(), caption))


# ---------- page helpers ----------

def graph_frame(page: Page) -> Frame:
    """The Three.js iframe is re-created on every Streamlit rerun, so look it up each time."""
    handle = page.locator("iframe").first.element_handle()
    frame = handle.content_frame()
    frame.wait_for_function("() => window.attackGraph && window.attackGraph.nodeCount > 0", timeout=30_000)
    return frame


def iframe_origin(page: Page) -> tuple[float, float]:
    box = page.locator("iframe").first.bounding_box()
    return box["x"], box["y"]


def scroll_to_text(page: Page, text: str) -> None:
    page.get_by_text(text, exact=False).first.scroll_into_view_if_needed()
    page.evaluate(
        """(t) => { const el = [...document.querySelectorAll('h1,h2,h3,p,span,div')]
                .find(e => e.childElementCount === 0 && e.textContent.includes(t));
                if (el) el.scrollIntoView({block: 'start'}); }""",
        text,
    )
    time.sleep(0.6)


def scroll_to_top(page: Page) -> None:
    scroll_to_text(page, "Security Attack Graph 3D")


def wait_for_result(page: Page) -> None:
    page.get_by_text("Top Risk Path").first.wait_for(timeout=RESULT_TIMEOUT_MS)
    page.get_by_text("Attack Path を探索中").first.wait_for(state="hidden", timeout=RESULT_TIMEOUT_MS)
    graph_frame(page)
    time.sleep(1.5)


def drag_rotate(rec: Recorder, caption: Caption, dx_total: float, steps: int) -> None:
    x0, y0 = iframe_origin(rec.page)
    cx, cy = x0 + 480, y0 + 330
    rec.page.mouse.move(cx, cy)
    rec.page.mouse.down()
    for i in range(1, steps + 1):
        rec.page.mouse.move(cx + dx_total * i / steps, cy + 40 * i / steps, steps=2)
        rec.capture_once(caption)
    rec.page.mouse.up()


def click_node(page: Page, node_id: str) -> None:
    pos = graph_frame(page).evaluate(f"() => window.attackGraph.screenPosition('{node_id}')")
    x0, y0 = iframe_origin(page)
    page.mouse.click(x0 + pos["x"], y0 + pos["y"])


def ask(page: Page, question: str) -> None:
    box = page.get_by_role("textbox", name="質問")
    box.fill(question)
    box.press("Enter")
    time.sleep(0.5)
    page.get_by_role("button", name="実行", exact=True).click()


def select_scenario(page: Page, label: str) -> None:
    page.get_by_role("combobox", name="シナリオ選択").click()
    page.get_by_role("option", name=label).click()
    page.get_by_text("Detail Panel").first.wait_for()
    graph_frame(page)
    time.sleep(1.5)


# ---------- scenes ----------

def record(page: Page, url: str) -> list[tuple[bytes, Caption]]:
    steps = 8
    rec = Recorder(page, steps)
    page.goto(url)
    page.get_by_text("クエリ例").first.wait_for(timeout=60_000)
    graph_frame(page)
    time.sleep(2)

    c = Caption(1, "ダミー企業ネットワークを知識グラフとして 3D 表示",
                "資産（青）・脆弱性（赤）・権限（紫/黄）・シークレット（橙）・データ（緑）を Neo4j に格納")
    rec.capture(3, c)
    drag_rotate(rec, Caption(1, c.title, "ドラッグで回転。左の Internet から右の Customer Data へ、攻撃が進む向きに並べている"),
                dx_total=260, steps=14)

    c = Caption(2, "自然言語で質問する", "「顧客データに到達する最も危険な経路は？」→ Qwen2.5-7B (vLLM) が意図・起点・終点を解釈")
    page.get_by_role("button", name="顧客データに到達する最も危険な経路は？", exact=True).click()
    rec.capture(2.5, c)
    wait_for_result(page)

    rec.capture(4.5, Caption(3, "最も危険な経路を赤くハイライト",
                             "Cypher で候補経路を探索し、脆弱性の深刻度・権限・データ重要度でスコアリングした Top 1"))

    scroll_to_text(page, "Result Summary")
    rec.capture(4.5, Caption(4, "結果サマリ：経路・スコア・説明文",
                             "説明文はグラフから組み立てるのでノード名・順序は常に正確"))

    # The AI explanation is already in view below the summary; only the caption changes.
    rec.capture(5, Caption(5, "AI 解説（guided decoding）",
                           "ノード名は JSON Schema の enum で経路から固定。LLM は各ステップの説明と根本原因・塞ぐ箇所だけを書く"))

    scroll_to_text(page, "経路一覧")
    page.get_by_text("Top 1 スコア内訳").first.click()
    time.sleep(0.8)
    rec.capture(4.5, Caption(6, "経路一覧とスコア内訳",
                             "2 位は Application 経由、3 位は VPN 経由。スコア = Σ脆弱性 + max(権限/データ/資産) − 経路長"))

    scroll_to_top(page)
    graph_frame(page)
    click_node(page, "a_svc")
    rec.capture(4.5, Caption(7, "ノードをクリックして詳細を見る",
                             "Service Account の隣接ノードだけを強調し、属性と権限（s3:GetObject）を表示"))

    c = Caption(8, "シナリオ切替：認可過剰（Scenario C）", "「機密テーブルに到達する最も危険な経路は？」")
    select_scenario(page, "Scenario C: 認可過剰")
    rec.capture(1.5, c)
    ask(page, "機密テーブルに到達する最も危険な経路は？")
    rec.capture(1.5, Caption(8, c.title, "推論中…（実際は 5〜10 秒。GIF では短縮）"))
    wait_for_result(page)
    rec.capture(4.5, Caption(8, c.title, "Internal User → Excessive Trust Policy → … → Sensitive Table が最も危険"))
    return rec.frames


# ---------- annotation & encoding ----------

def annotate(png: bytes, caption: Caption, total_steps: int) -> Image.Image:
    image = Image.open(io.BytesIO(png)).convert("RGB")
    image = image.resize((OUT_WIDTH, round(image.height * OUT_WIDTH / image.width)), Image.LANCZOS)
    canvas = Image.new("RGB", (image.width, image.height + BANNER_HEIGHT), (11, 16, 32))
    canvas.paste(image, (0, 0))
    draw = ImageDraw.Draw(canvas)
    top = image.height
    draw.rectangle([0, top, canvas.width, top + 4], fill=(239, 68, 68))
    _draw_badge(draw, f"STEP {caption.step}/{total_steps}", (16, top + 18))
    draw.text((132, top + 14), caption.title, font=ImageFont.truetype(FONT_BOLD, 22, index=0), fill=(255, 255, 255))
    draw.text((132, top + 52), caption.body, font=ImageFont.truetype(FONT_REGULAR, 15, index=0), fill=(203, 213, 225))
    return canvas


def _draw_badge(draw: ImageDraw.ImageDraw, text: str, xy: tuple[int, int]) -> None:
    font = ImageFont.truetype(FONT_BOLD, 15, index=0)
    x, y = xy
    width = draw.textlength(text, font=font)
    draw.rounded_rectangle([x, y, x + width + 20, y + 30], radius=6, fill=(239, 68, 68))
    draw.text((x + 10, y + 4), text, font=font, fill=(255, 255, 255))


def encode_gif(frames: list[Image.Image], out: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        for i, frame in enumerate(frames):
            frame.save(Path(tmp) / f"f{i:04d}.png")
        pattern = str(Path(tmp) / "f%04d.png")
        palette = str(Path(tmp) / "palette.png")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", pattern,
                        "-vf", "palettegen=stats_mode=diff:max_colors=192", palette], check=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", pattern, "-i", palette,
                        "-lavfi", "paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle", "-loop", "0", str(out)],
                       check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8501")
    parser.add_argument("--out", type=Path, default=Path("docs/images/demo.gif"))
    args = parser.parse_args()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
        page = browser.new_page(viewport=VIEWPORT, device_scale_factor=1)
        raw = record(page, args.url)
        browser.close()
    total = max(c.step for _, c in raw)
    encode_gif([annotate(png, c, total) for png, c in raw], args.out)
    size_mb = args.out.stat().st_size / 1_000_000
    print(f"wrote {args.out} ({len(raw)} frames, {len(raw) / FPS:.1f}s, {size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
