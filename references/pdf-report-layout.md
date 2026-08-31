# Miaoda PDF Report Layout

Use this reference when producing a PDF拆解文档 from a Miaoda case, Douyin link, or local video.

## Required Content

Keep the PDF focused on these sections:

- `标题`
- `类目`
- extracted frame images replacing the app's playable video area
- `爆款内容分析`
- `前3秒口播参考`

Remove or demote non-requested elements from the primary layout. Do not include `达人昵称`, raw metric dashboards, buttons, side controls, or app chrome unless the user asks for them.

Treat the reference image as layout/color inspiration only. If a completed skill breakdown does not contain an element from the screenshot, do not recreate that element just to match the screenshot. In particular, omit the close icon, video player controls, floating Miaoda badges, `查看原始视频`, side toolbars, and standalone 达人 information by default.

## Visual Direction

Match the Miaoda detail-card feel shown in the user's reference image:

- White page background.
- Large, dark, bold title at the top.
- Category/industry/creative-direction chips directly below the title.
- Chip colors should mix warm gold, purple, and blue instead of using a single-hue palette.
- Replace the video player with extracted frame images; do not preserve player UI, controls, or a fake video container.
- Use light lavender section backgrounds with subtle purple borders.
- Use white inner text blocks inside lavender sections.
- Use purple section headings, with small icon-like marks only when they stay clean in PDF.
- Keep generous spacing, but avoid landing-page hero treatment or decorative blobs.

Recommended colors:

- Text: `#141827`
- Muted text: `#596074`
- Purple accent: `#7B4DFF`
- Purple border: `#E4D6FF`
- Lavender panel: `#FBF7FF`
- Gold chip text/border: `#A97816` / `#F4DEAA`
- Blue chip text/border: `#3A6FDA` / `#CDE0FF`
- Black frame band: `#050505`, only for fallback/empty states or when the user explicitly wants a player-like frame.

## Frame Area

For local videos, extract all visually distinct scenes needed to understand the video, not just a fixed small representative subset. Label every extracted frame with its timestamp, such as `0s`, `1s`, `4.5s`, or `11.2s`. Use actual frames; do not use the original video player UI. Choose the frame count, columns, and page breaks according to the PDF page size so the images are large, edge-aligned with the content column, and not awkwardly shrunk.

For A4 portrait reports, the default extracted-frame grid is 4 images per row. The last row may contain fewer images; do not add placeholders or filler images. Keep the extracted-frame area within 2 PDF pages whenever practical. If the complete set of visually distinct frames is too large to fit cleanly in 2 pages at 4 columns, switch to 5 images per row and paginate the remaining frames before the analysis sections. For vertical short videos, a useful density target is up to 8 frames per page at 4 columns, or up to 15 frames per page at 5 columns when 2-page compression is needed.

If the user provides a ready-made montage/reference frame image, place that image directly in the PDF: do not add a black outer frame, rounded player container, individual frame cards, or selection markers. If the montage becomes too small because it is too tall for the page, extract a smaller number of frames from the source video and rebuild an edge-aligned grid instead.

For remote links that cannot be downloaded in the current environment, show a black band with a concise unavailable note. Include the source link only if the user asks for it or the caller enables it explicitly.

## Section Content

`爆款内容分析` should be a concise structured paragraph or bullet-style blocks using the app's own mental model where evidence permits: `前3s`, `中段`, `结尾`, `机制引入`, `机制讲解`, pain point, proof, offer, and conversion cue.

`前3秒口播参考` should include:

- opening-hook labels when available, such as `反差对比` or `倍数效果对比`
- `原始口播`
- `仿写示例` or reusable口播模板

Omit optional inner elements when no evidence is available. For example, do not create hook labels only because the screenshot has pills.

For local videos, establish `原始口播` from evidence before writing it into the PDF: inspect the opening subtitle frames and run or consult audio ASR when audio is available. Prefer wording confirmed by both sources. If ASR has obvious homophone mistakes that the subtitle resolves, use the subtitle-corrected wording. If only subtitles are available, or if the line is inferred from visuals rather than heard speech, label it as inferred rather than exact.

## Generation Notes

Prefer HTML/CSS rendered through local Chrome for Chinese PDF output. Avoid ReportLab for Chinese-heavy reports unless a reliable CJK font is explicitly registered and rendering has been visually verified.

After creating a PDF, render at least the first page to PNG with Poppler and inspect it for clipped Chinese text, broken image placement, overlapping cards, and missing frame images.
