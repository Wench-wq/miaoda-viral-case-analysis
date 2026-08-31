# miaoda-viral-case-analysis

Codex skill for searching, analyzing, and exporting Miaoda 千川星选爆款内容榜单 case-analysis videos as compact PDF reports with extracted video frames.

## What It Does

- Retrieves or mirrors 妙搭「爆款案例分析」case fields.
- Breaks down local or linked short videos into Miaoda-style reports.
- Exports PDF reports with title, category chips, extracted frame grids, 爆款内容分析, and 前3秒口播参考.
- Uses audio ASR plus visible subtitles to confirm opening speech when local video audio is available.

## Install

Copy this folder into your Codex skills directory:

```bash
cp -R miaoda-viral-case-analysis ~/.codex/skills/
```

Then invoke it in Codex:

```text
Use $miaoda-viral-case-analysis to 拆解这个视频并输出 PDF。
```

## Notes

This skill does not include credentials. Live Miaoda retrieval depends on the user's own authenticated access to the source app.
