#!/usr/bin/env python3
"""Generate a Miaoda-style PDF video case-analysis report."""

from __future__ import annotations

import argparse
import html
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


DEFAULT_CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_FRAME_COLUMNS = 4
DEFAULT_FRAME_MAX_PER_PAGE = 8
COMPRESSED_FRAME_COLUMNS = 5
COMPRESSED_FRAME_MAX_PER_PAGE = 15


def as_list(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def first_present(data: dict[str, Any], keys: list[str], default: str = "") -> str:
    for key in keys:
        value = data.get(key)
        if value not in (None, "", []):
            return str(value)
    return default


def local_or_url_to_src(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https", "data", "file"}:
        return value
    return Path(value).expanduser().resolve().as_uri()


def find_ffmpeg() -> str | None:
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg  # type: ignore

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def find_ffprobe(ffmpeg_path: str | None) -> str | None:
    found = shutil.which("ffprobe")
    if found:
        return found
    if ffmpeg_path:
        candidate = Path(ffmpeg_path).with_name("ffprobe")
        if candidate.exists():
            return str(candidate)
    return None


def probe_duration(video_path: Path, ffprobe: str | None) -> float | None:
    if not ffprobe:
        return None
    cmd = [
        ffprobe,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return float(result.stdout.strip())
    except Exception:
        return None


def format_timestamp(value: float) -> str:
    text = f"{value:.1f}".rstrip("0").rstrip(".")
    return f"{text}s"


def parse_timestamps(value: Any) -> list[float]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        parts = value
    else:
        parts = str(value).replace("，", ",").split(",")
    timestamps: list[float] = []
    for part in parts:
        text = str(part).strip().rstrip("sS秒")
        if not text:
            continue
        timestamps.append(float(text))
    return timestamps


def extract_frames(
    video: str,
    out_dir: Path,
    count: int = 6,
    timestamps: list[float] | None = None,
) -> list[str]:
    video_path = Path(video).expanduser().resolve()
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to extract video frames")

    out_dir.mkdir(parents=True, exist_ok=True)
    duration = probe_duration(video_path, find_ffprobe(ffmpeg))
    if timestamps:
        times = timestamps
    elif duration and duration > 0:
        start = min(0.35, duration * 0.08)
        end = max(start, duration - min(0.35, duration * 0.08))
        if count == 1:
            times = [duration / 2]
        else:
            step = (end - start) / max(count - 1, 1)
            times = [start + step * i for i in range(count)]
    else:
        times = [i * 1.0 for i in range(count)]

    frames: list[str] = []
    for idx, timestamp in enumerate(times, start=1):
        label = format_timestamp(timestamp).replace(".", "_")
        frame_path = out_dir / f"frame_{idx:02d}_{label}.jpg"
        cmd = [
            ffmpeg,
            "-y",
            "-ss",
            f"{timestamp:.3f}",
            "-i",
            str(video_path),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(frame_path),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        if frame_path.exists() and frame_path.stat().st_size > 0:
            frames.append(str(frame_path))
    if not frames:
        raise RuntimeError("No frames were extracted from the video")
    return frames


def paragraphs(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value or "").strip()
    if not text:
        return []
    chunks = [part.strip() for part in text.replace("\r\n", "\n").split("\n") if part.strip()]
    return chunks or [text]


def pill_html(labels: list[str]) -> str:
    classes = ["gold", "purple", "blue"]
    output = []
    for index, label in enumerate(labels):
        output.append(
            f'<span class="pill {classes[index % len(classes)]}">{html.escape(label)}</span>'
        )
    return "\n".join(output)


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value in (None, ""):
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def frame_items(data: dict[str, Any]) -> list[dict[str, str]]:
    raw_items = data.get("frame_items") or data.get("frames_with_times")
    if isinstance(raw_items, list):
        items: list[dict[str, str]] = []
        for item in raw_items:
            if isinstance(item, dict):
                path = first_present(item, ["path", "src", "frame", "image"])
                label = first_present(item, ["label", "time", "timestamp"])
                if path:
                    items.append({"path": path, "label": label})
        if items:
            return items

    frames = as_list(data.get("frames") or data.get("frame_paths") or data.get("app3sPicture"))
    labels = as_list(data.get("frame_labels") or data.get("frame_times") or data.get("timestamps"))
    return [
        {"path": frame, "label": labels[idx] if idx < len(labels) else ""}
        for idx, frame in enumerate(frames)
    ]


def frames_html(items: list[dict[str, str]], plain: bool = False) -> str:
    if not items:
        return '<div class="frame-empty">未能获取视频抽帧图像</div>'
    imgs = []
    for idx, item in enumerate(items, start=1):
        src = local_or_url_to_src(item["path"])
        label = item.get("label") or ("" if plain else f"Frame {idx:02d}")
        caption_class = "time-label" if plain else ""
        caption = (
            f'<figcaption class="{caption_class}">{html.escape(label)}</figcaption>'
            if label
            else ""
        )
        imgs.append(
            '<figure class="frame-card">'
            f'<img src="{html.escape(src)}" alt="视频抽帧 {idx}">'
            f"{caption}"
            "</figure>"
        )
    return "\n".join(imgs)


def chunked(items: list[dict[str, str]], size: int) -> list[list[dict[str, str]]]:
    if size <= 0:
        return [items]
    return [items[idx : idx + size] for idx in range(0, len(items), size)]


def recommended_frame_layout(item_count: int) -> tuple[int, int]:
    if item_count > DEFAULT_FRAME_MAX_PER_PAGE * 2:
        return COMPRESSED_FRAME_COLUMNS, COMPRESSED_FRAME_MAX_PER_PAGE
    return DEFAULT_FRAME_COLUMNS, DEFAULT_FRAME_MAX_PER_PAGE


def media_sections_html(
    media_class: str,
    media_style: str,
    chunks: list[str],
) -> str:
    sections = []
    for idx, body in enumerate(chunks):
        page_break = " frame-page-break" if idx < len(chunks) - 1 else ""
        continued = " frame-page-continued" if idx > 0 else ""
        sections.append(
            f'<section class="{media_class}{page_break}{continued}"{media_style} aria-label="视频抽帧图像">\n'
            f"{body}\n"
            "</section>"
        )
    return "\n".join(sections)


def montage_html(montage: str) -> str:
    src = local_or_url_to_src(montage)
    return (
        '<div class="montage-wrap">'
        f'<img class="montage-image" src="{html.escape(src)}" alt="视频抽帧图像">'
        "</div>"
    )


def analysis_html(analysis: Any) -> str:
    items = paragraphs(analysis)
    if not items:
        return '<div class="inner-card muted">暂无爆款内容分析，请补充榜单字段或人工拆解结论。</div>'
    return "\n".join(
        f'<div class="inner-card">{html.escape(item)}</div>' for item in items
    )


def pre3s_html(value: Any) -> str:
    if isinstance(value, dict):
        hook_tags = as_list(value.get("hook_tags") or value.get("hookTags"))
        original = first_present(value, ["original", "原始口播", "pre3sScript", "pre3s_script"])
        rewrite = first_present(value, ["rewrite", "仿写示例", "example", "template"])
        inferred = bool(value.get("inferred"))
    else:
        hook_tags = []
        original = "\n".join(paragraphs(value))
        rewrite = ""
        inferred = False

    rows = []
    if hook_tags:
        rows.append(f'<div class="hook-row">{pill_html(hook_tags)}</div>')
    if inferred:
        rows.append('<div class="note">以下口播根据字幕/ASR 推断，不等同于逐字转写。</div>')
    if original:
        rows.append(
            '<div class="inner-card"><div class="label purple-text">原始口播</div>'
            f'<p>{html.escape(original)}</p></div>'
        )
    if rewrite:
        rows.append(
            '<div class="inner-card"><div class="label blue-text">仿写示例</div>'
            f'<p>{html.escape(rewrite)}</p></div>'
        )
    if not rows:
        rows.append('<div class="inner-card muted">暂无前 3 秒口播参考。</div>')
    return "\n".join(rows)


def build_html(data: dict[str, Any], show_source_link: bool = False) -> str:
    title = first_present(data, ["title", "videoTitle"], "爆款案例拆解")
    source_url = first_present(data, ["source_url", "sourceUrl", "videoLink", "douyin_url"])
    category_labels: list[str] = []
    for key in ["industry", "category", "productSubCategory", "creativeDirection"]:
        category_labels.extend(as_list(data.get(key)))
    category_labels.extend(as_list(data.get("tags")))
    if not category_labels:
        category_labels = ["未标注类目"]

    montage = first_present(data, ["montage", "montage_path", "frame_montage"])
    analysis = data.get("analysis") or data.get("bestsellerContentAnalysis")
    pre3s = data.get("pre3s") or data.get("pre3sScript") or data.get("pre3s_script")
    plain_frame_grid = truthy(data.get("plain_frame_grid") or data.get("edge_aligned_frames"))
    items = frame_items(data)
    auto_columns, auto_max_per_page = recommended_frame_layout(len(items))
    frame_columns = int(data.get("frame_columns") or auto_columns)
    if montage:
        media_class = "frame-band montage"
        media_chunks = [montage_html(montage)]
    elif plain_frame_grid:
        media_class = "frame-band plain-grid"
        max_per_page = int(data.get("frame_max_per_page") or auto_max_per_page)
        media_chunks = [
            frames_html(chunk, plain=True)
            for chunk in chunked(items, max_per_page)
        ]
    else:
        media_class = "frame-band"
        media_chunks = [frames_html(items)]
    media_style = f' style="--frame-columns: {max(1, min(frame_columns, 5))};"'
    media_sections = media_sections_html(media_class, media_style, media_chunks)

    source_link = ""
    if show_source_link and source_url:
        source_link = (
            f'<a class="source-link" href="{html.escape(source_url)}">查看原始视频</a>'
        )

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>{html.escape(title)}</title>
  <style>
    @page {{ size: A4; margin: 0; }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: #ffffff;
      color: #141827;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
        "Hiragino Sans GB", "Microsoft YaHei", Arial, sans-serif;
      letter-spacing: 0;
    }}
    .page {{
      width: 210mm;
      min-height: 297mm;
      padding: 18mm 16mm 16mm;
      background: #ffffff;
    }}
    h1 {{
      margin: 0 0 9mm;
      font-size: 25px;
      line-height: 1.25;
      font-weight: 800;
      color: #141827;
    }}
    .pills {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 13mm;
    }}
    .pill {{
      display: inline-flex;
      align-items: center;
      min-height: 28px;
      padding: 3px 12px 4px;
      border-radius: 999px;
      border: 1px solid transparent;
      font-size: 15px;
      line-height: 1.2;
      font-weight: 700;
      background: #fff;
      white-space: nowrap;
    }}
    .pill.gold {{ color: #a97816; border-color: #f4deaa; background: #fffaf0; }}
    .pill.purple {{ color: #7b4dff; border-color: #d9c8ff; background: #f7f1ff; }}
    .pill.blue {{ color: #3a6fda; border-color: #cde0ff; background: #f1f7ff; }}
    .frame-band {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
      min-height: 94mm;
      padding: 9px;
      margin-bottom: 11mm;
      border-radius: 18px;
      background: #050505;
      overflow: hidden;
      page-break-inside: avoid;
    }}
    .frame-card {{
      margin: 0;
      min-width: 0;
      height: 43mm;
      position: relative;
      overflow: hidden;
      border-radius: 10px;
      background: #111;
    }}
    .frame-card img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }}
    .frame-card figcaption {{
      position: absolute;
      left: 7px;
      bottom: 6px;
      padding: 2px 6px;
      border-radius: 999px;
      color: #fff;
      background: rgba(0, 0, 0, .58);
      font-size: 8px;
      line-height: 1.2;
    }}
    .frame-card figcaption.time-label {{
      left: 6px;
      top: 6px;
      bottom: auto;
      padding: 2px 6px;
      border-radius: 4px;
      color: #ffffff;
      background: rgba(123, 77, 255, .88);
      font-size: 9px;
      font-weight: 700;
    }}
    .frame-empty {{
      grid-column: 1 / -1;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 88mm;
      color: #ffffff;
      font-size: 15px;
    }}
    .frame-band.montage {{
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 0;
      padding: 0;
      border-radius: 0;
      background: transparent;
      overflow: visible;
    }}
    .montage-wrap {{
      width: 100%;
      display: flex;
      justify-content: center;
      overflow: visible;
      border-radius: 0;
      background: transparent;
    }}
    .montage-image {{
      display: block;
      max-width: 100%;
      max-height: 205mm;
      width: auto;
      height: auto;
      object-fit: contain;
    }}
    .frame-band.plain-grid {{
      grid-template-columns: repeat(var(--frame-columns, 4), minmax(0, 1fr));
      gap: 0;
      min-height: 0;
      padding: 0;
      border-radius: 0;
      background: transparent;
      overflow: visible;
      width: 100%;
    }}
    .frame-band.plain-grid .frame-card {{
      height: auto;
      aspect-ratio: 9 / 16;
      border-radius: 0;
      background: transparent;
    }}
    .frame-band.plain-grid .frame-card img {{
      object-fit: cover;
    }}
    .frame-band.frame-page-break {{
      break-after: page;
    }}
    .frame-band.frame-page-continued {{
      margin-top: 18mm;
    }}
    .source-link {{
      display: inline-block;
      margin: -5mm 0 9mm;
      color: #7b4dff;
      font-size: 14px;
      font-weight: 700;
      text-decoration: none;
    }}
    .section {{
      margin-bottom: 10mm;
      padding: 9mm;
      border: 1px solid #e4d6ff;
      border-radius: 15px;
      background: #fbf7ff;
      page-break-inside: avoid;
    }}
    .section h2 {{
      margin: 0 0 7mm;
      color: #7b4dff;
      font-size: 18px;
      line-height: 1.2;
      font-weight: 800;
    }}
    .inner-card {{
      margin-top: 6px;
      padding: 7mm;
      border-radius: 12px;
      background: rgba(255, 255, 255, .92);
      color: #303648;
      font-size: 15px;
      line-height: 1.7;
      font-weight: 600;
    }}
    .inner-card:first-of-type {{ margin-top: 0; }}
    .inner-card p {{ margin: 4px 0 0; }}
    .label {{
      margin-bottom: 2mm;
      font-size: 13px;
      font-weight: 800;
    }}
    .purple-text {{ color: #a645c8; }}
    .blue-text {{ color: #3a6fda; }}
    .hook-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 6px;
    }}
    .note {{
      color: #596074;
      font-size: 12px;
      margin: 2mm 0;
    }}
    .muted {{ color: #596074; }}
  </style>
</head>
<body>
  <main class="page">
    <h1>{html.escape(title)}</h1>
    <div class="pills">{pill_html(category_labels)}</div>
    {media_sections}
    {source_link}
    <section class="section">
      <h2>爆款内容分析</h2>
      {analysis_html(analysis)}
    </section>
    <section class="section">
      <h2>前3秒口播参考</h2>
      {pre3s_html(pre3s)}
    </section>
  </main>
</body>
</html>
"""


def find_chrome() -> str:
    env_chrome = os.environ.get("CHROME") or os.environ.get("GOOGLE_CHROME_BIN")
    candidates = [
        env_chrome,
        DEFAULT_CHROME,
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        shutil.which("chrome"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(candidate)
    raise RuntimeError("Could not find Chrome/Chromium for PDF rendering")


def print_pdf(html_path: Path, output_path: Path) -> None:
    chrome = find_chrome()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        chrome,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--print-to-pdf-no-header",
        f"--print-to-pdf={output_path}",
        "--virtual-time-budget=1000",
        html_path.as_uri(),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def render_preview(pdf_path: Path, output_dir: Path) -> Path | None:
    pdftoppm = shutil.which("pdftoppm")
    if not pdftoppm:
        bundled = Path(
            "/Users/chuchu/.cache/codex-runtimes/codex-primary-runtime/"
            "dependencies/bin/override/pdftoppm"
        )
        if bundled.exists():
            pdftoppm = str(bundled)
    if not pdftoppm:
        return None
    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = output_dir / pdf_path.stem
    subprocess.run(
        [pdftoppm, "-png", "-f", "1", "-singlefile", str(pdf_path), str(prefix)],
        check=True,
        capture_output=True,
    )
    preview = prefix.with_suffix(".png")
    return preview if preview.exists() else None


def load_data(args: argparse.Namespace) -> dict[str, Any]:
    data: dict[str, Any] = {}
    if args.input_json:
        with open(args.input_json, "r", encoding="utf-8") as handle:
            data.update(json.load(handle))

    for key in ["title", "industry", "category", "creative_direction", "analysis", "source_url"]:
        value = getattr(args, key)
        if value:
            data_key = "creativeDirection" if key == "creative_direction" else key
            data[data_key] = value
    if args.tag:
        data["tags"] = as_list(data.get("tags")) + args.tag
    if args.frame:
        data["frames"] = as_list(data.get("frames")) + args.frame
    if args.montage:
        data["montage"] = args.montage
    if args.plain_frame_grid:
        data["plain_frame_grid"] = True
    if args.frame_columns:
        data["frame_columns"] = args.frame_columns
    if args.frame_max_per_page:
        data["frame_max_per_page"] = args.frame_max_per_page
    if args.timestamps:
        data["timestamps"] = [format_timestamp(item) for item in parse_timestamps(args.timestamps)]
    if args.pre3s:
        data["pre3s"] = args.pre3s

    video = args.video or data.get("video") or data.get("video_path")
    has_montage = first_present(data, ["montage", "montage_path", "frame_montage"])
    if video and not as_list(data.get("frames")) and not has_montage:
        frame_dir = Path(args.frame_dir) if args.frame_dir else Path(tempfile.mkdtemp(prefix="miaoda_frames_"))
        requested_times = parse_timestamps(args.timestamps or data.get("timestamps"))
        data["frames"] = extract_frames(
            str(video),
            frame_dir,
            args.frame_count,
            timestamps=requested_times or None,
        )
        if requested_times:
            data["frame_times"] = [format_timestamp(item) for item in requested_times]
        data.setdefault("plain_frame_grid", True)
        items = frame_items(data)
        frame_columns, frame_max_per_page = recommended_frame_layout(len(items))
        data.setdefault("frame_columns", frame_columns)
        data.setdefault("frame_max_per_page", frame_max_per_page)
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a Miaoda-style PDF report.")
    parser.add_argument("--input-json", help="Report data JSON file")
    parser.add_argument("--output", required=True, help="Output PDF path")
    parser.add_argument("--title")
    parser.add_argument("--industry")
    parser.add_argument("--category")
    parser.add_argument("--creative-direction")
    parser.add_argument("--tag", action="append", help="Additional category/tag pill")
    parser.add_argument("--video", help="Local video path for frame extraction")
    parser.add_argument("--frame", action="append", help="Pre-extracted frame path or URL")
    parser.add_argument("--montage", help="A ready-made frame montage image to place directly in the PDF")
    parser.add_argument("--frame-count", type=int, default=6)
    parser.add_argument(
        "--timestamps",
        help="Comma-separated timestamps to extract, e.g. 0,1,2,3,4.5,6,8,10,11.2",
    )
    parser.add_argument(
        "--plain-frame-grid",
        action="store_true",
        help="Lay extracted frames directly edge-to-edge without a black player frame.",
    )
    parser.add_argument("--frame-columns", type=int, help="Number of columns for frame grid")
    parser.add_argument(
        "--frame-max-per-page",
        type=int,
        help="Maximum frame images per page before continuing on a new page.",
    )
    parser.add_argument("--frame-dir", help="Directory for extracted frames")
    parser.add_argument("--analysis")
    parser.add_argument("--pre3s")
    parser.add_argument("--source-url")
    parser.add_argument(
        "--show-source-link",
        action="store_true",
        help="Show 查看原始视频 link; omitted by default to keep the PDF to requested elements.",
    )
    parser.add_argument("--keep-html", action="store_true")
    parser.add_argument("--render-preview", action="store_true")
    args = parser.parse_args()

    try:
        data = load_data(args)
        output_path = Path(args.output).expanduser().resolve()
        with tempfile.TemporaryDirectory(prefix="miaoda_pdf_") as tmp:
            html_path = Path(tmp) / "report.html"
            html_path.write_text(
                build_html(data, show_source_link=args.show_source_link),
                encoding="utf-8",
            )
            print_pdf(html_path, output_path)
            if args.keep_html:
                html_copy = output_path.with_suffix(".html")
                shutil.copyfile(html_path, html_copy)
            preview = None
            if args.render_preview:
                preview = render_preview(output_path, output_path.parent / "_previews")
        print(json.dumps({"pdf": str(output_path), "preview": str(preview) if preview else None}, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(f"miaoda_pdf_report.py: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
