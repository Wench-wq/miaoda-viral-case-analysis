---
name: miaoda-viral-case-analysis
description: Search, analyze, and export Miaoda 千川星选爆款内容榜单 case-analysis videos as compact PDF reports with extracted video frames.
---

# Miaoda Viral Case Analysis

Use this skill when the user asks to检索,筛选,提炼,分析, or复刻妙搭「千川星选爆款内容榜单」里的「爆款案例分析」功能, especially requests such as:

- 按类目查找爆款视频案例
- 搜索某个品牌、产品、达人、脚本钩子、创意方向
- 输出视频卡片列表、PDF 拆解报告、爆款内容分析、前 3 秒话术、深度拆解
- 对比不同类目或时间范围的爆款案例

## Source App

Default app URL:

`https://bytedance.feishuapp.com/app/app_179zmr1x048/hot-rank`

The visible「爆款案例分析」tab uses:

- Time ranges: `7d` = 近一周, `30d` = 近一个月
- Top-level industry tabs: `全部`, `个护美妆`, `家清纸品`, `服饰&家居电器`, `母婴宠物`, `食品饮料`
- Video cards: rank, thumbnail/video, title, industry, category, creative direction, 爆款内容分析, and 查看深度拆解
- Detail fields: ASR text, pre-3-second script, opening hook levels, Douyin video link, duration, CTR/CVR/PVR, star/达人 nickname, 星川消耗量级, and app-hosted media URLs when available

For implementation details and endpoint fields, read [references/miaoda-hot-rank.md](references/miaoda-hot-rank.md) when performing live retrieval, debugging API calls, or explaining how the mirrored workflow works.

## Recommended Workflow

Prefer live app data over remembered examples. The ranking changes over time, so fetch current data whenever the user asks for latest/current results or does not provide a saved export.

1. Normalize the user request into app filters:
   - `全部`: omit `industry`
   - category tabs map to `industry`
   - use `timeRange=7d` unless the user asks for 近一个月/30 天
   - keep user keywords as post-fetch search terms unless they clearly name an exact API filter
2. Fetch data through the Miaoda app API using the CSRF flow from the page. The helper script handles this:

```bash
python3 /Users/chuchu/.codex/skills/miaoda-viral-case-analysis/scripts/miaoda_hot_rank.py --industry 食品饮料 --time-range 7d --limit 10
```

3. If the API is unavailable because the user is not logged in, access is restricted, or CSRF changes, use the rendered page as a fallback with browser/scrape tools and parse the visible cards. Do not bypass authentication or invent missing private data.
4. For a compact result, return the same mental model as the app card: `rank`, title, industry/category, creative direction, 爆款内容分析, 前 3 秒脚本, metrics, and Douyin/app media links.
5. For “深度拆解”, fetch each selected detail by `id` with `--detail <id>` or use `--details` during list retrieval when the user needs ASR/opening-hook fields.

## PDF Reports

When the user asks to拆解 a video/case, requests a report/PDF/document, or provides a local video file with this skill, make the deliverable a PDF by default. Read [references/pdf-report-layout.md](references/pdf-report-layout.md) before authoring the PDF.

Use the helper when possible:

```bash
python3 /Users/chuchu/.codex/skills/miaoda-viral-case-analysis/scripts/miaoda_pdf_report.py --input-json report-data.json --output output/pdf/report.pdf
```

If a local video is provided, extract real frame images and place those frames in the media area. Do not embed a playable video element in the PDF. If frames cannot be extracted from a remote Douyin/app link, state the limitation in the PDF and include the source link only when the user asks for it.

For frame-heavy local-video breakdowns, include all visually distinct scenes from the video, not just a small representative subset. Label every extracted image with its timestamp, and choose the number of columns/pages according to A4 page capacity so frames stay large and edge-aligned. For ordinary A4 portrait PDF reports, lay extracted frames in rows of 4 images by default; the last row may contain fewer images. Keep the extracted-frame area within 2 PDF pages whenever practical. If the required distinct frames cannot fit cleanly within 2 pages at 4 columns, switch that report's frame grid to 5 images per row.

For `前3秒口播参考` in local-video reports, confirm the opening speech from both audio transcription/ASR and the visible subtitle frames whenever audio is available. Do not use a visually inferred or generic opening line as `原始口播` when the video contains actual speech or subtitles. If ASR and subtitles disagree, use the version best supported by the audio, correct obvious ASR homophone errors from the on-screen subtitles, and label uncertain wording as inferred.

The reference screenshot is a visual style guide, not a component checklist. Do not add screenshot-only elements that are absent from the skill's completed breakdown, such as player controls, close buttons, floating app badges, `查看原始视频`, 达人 cards, or extra metric panels.

## Output Style

Keep outputs useful for content work:

- Start with the query scope: time range, industry/category, keyword, result count.
- Show ranked results rather than unordered summaries.
- Preserve the app’s terminology: `爆款内容分析`, `前3s`, `中段`, `结尾`, `机制引入`, `机制讲解`, etc.
- Include direct Douyin links when present.
- When reporting metrics, format CTR/CVR/PVR as percentages and 星川消耗 as a numeric level, not as a claim of exact spend unless the app labels it that way.

If the user asks to turn results into strategy, scripts, or a report, first retrieve or inspect the source case/video with this skill, then use the retrieved evidence and extracted frames for the downstream deliverable.
