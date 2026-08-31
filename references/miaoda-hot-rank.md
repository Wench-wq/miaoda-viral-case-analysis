# Miaoda Hot Rank Reference

This skill mirrors the「爆款案例分析」tab of the Miaoda app「千川星选爆款内容榜单」.

## App Observations

Observed app title: `千川星选爆款内容榜单`

Observed page subtitle: `发现热门创意，洞察爆款趋势`

Observed tabs:

- `爆款案例分析`
- `跑量内容公式`

Observed case-analysis filters:

- `近一周`
- `近一个月`
- `个护美妆`
- `家清纸品`
- `服饰&家居电器`
- `母婴宠物`
- `食品饮料`
- `全部`

The case card UI shows:

- rank badge
- app-hosted image/video preview
- video title
- industry and creative-direction chips
- `爆款内容分析`
- shortened analysis text with `前3s`, `中段`, and sometimes `结尾`
- `查看深度拆解` action

## Runtime Routes

Frontend routes observed in the bundled app:

- `/`
- `/hot-rank`
- `/hot-rank/formula/:videoId`

The app uses this base URL for API requests:

`https://bytedance.feishuapp.com/app/app_179zmr1x048`

## CSRF Flow

The API rejects naked requests with `Forbidden，csrf token not found`.

To call the API:

1. GET the app page and keep cookies.
2. Extract `window.csrfToken = "...";` from the returned HTML.
3. Send API requests with the same cookie jar and header:

`X-Suda-Csrf-Token: <token>`

Useful additional headers:

- `X-Page-Route: /app/app_179zmr1x048/hot-rank`
- `Referer: https://bytedance.feishuapp.com/app/app_179zmr1x048/hot-rank`

Do not try to bypass auth if the app starts requiring a logged-in account. Ask the user to log in in the in-app browser or provide an export.

## Case-Analysis Endpoints

Observed endpoints:

- `GET /api/rank/filter-options`
- `GET /api/rank/videos`
- `GET /api/rank/videos/:id`
- `GET /api/rank/statistics`
- `GET /api/rank/pre3s-hook-distribution`
- `GET /api/rank/word-cloud`
- `GET /api/rank/tag-combination`
- `GET /api/rank/pre3s-script-examples`
- `GET /api/rank/video-type-distribution`
- `GET /api/rank/creative-direction-distribution`
- `GET /api/rank/high-score-formulas`
- `GET /api/rank/high-score-formulas-filters`
- `GET /api/rank/interaction-curve/:videoId`
- `GET /api/rank/refresh-oral-broadcast`

For「爆款案例分析」search, the most important endpoints are `filter-options`, `videos`, and `videos/:id`.

## `/api/rank/videos` Parameters

The bundled app passes these query params when present:

- `industry`
- `category`
- `productSubCategory`
- `creativeDirection`
- `sortField`
- `sortOrder`
- `cursor`
- `timeRange`
- `pageSize`, default `20`

Use `industry` for the visible top-level tabs:

- `个护美妆`
- `家清纸品`
- `服饰&家居电器`
- `母婴宠物`
- `食品饮料`

Use no `industry` for `全部`.

## Common Response Fields

List records may include:

- `id`
- `rank`
- `videoTitle`
- `industry`
- `category`
- `productSubCategory`
- `creativeDirection`
- `xingchuanConsumptionLevel`
- `xingtuInfluencerNickname`
- `playCount3s`
- `playCount5s`
- `ctr`
- `cvr`
- `pvr`
- `app3sPicture`
- `appVideo`
- `videoLink`
- `videoDuration`
- `isLiveGraph`
- `isAgencyDistribution`
- `bestsellerContentAnalysis`
- `industryConsumptionRank`
- `industryAvgXingchuanConsumption`
- `videoType`
- `pre3sScript`

Detail records may add:

- `asrText`
- `pre3sRefSpeech1`
- `pre3sRefSpeech2`
- `openingHookLevel1`
- `openingHookLevel2`

## Search Behavior

For user-facing search, combine API filters with local keyword search:

- API filters: time range, industry, category, product subcategory, creative direction, sort, page size, pagination cursor
- Local keyword fields: title, industry, category, product subcategory, creative direction, influencer, bestseller analysis, pre-3-second script, ASR text when details are loaded

When the user asks for “不同类目中的视频”, query each requested industry independently and present grouped ranked results. Do not merge rankings across industries unless the user asks for a combined view.
