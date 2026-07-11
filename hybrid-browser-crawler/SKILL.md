---
name: hybrid-browser-crawler
description: browser-use + Crawl4AI 混合网页采集。核心打法——browser-use 只解决"人类交互难点"(登录/弹窗/复杂表单/导航)并产出身份(storage_state.json 或持久 profile)与种子 URL，Crawl4AI 吃这份登录态做规模化采集(deep crawl / 并发 arun_many / CSS schema 结构化抽取) → Markdown 或 JSONL。三段式：login(开锁) → map(发现链接) → crawl(规模抓取)。当用户要"抓需要登录的站/会员站/SaaS 后台数据"、"批量把网页转 Markdown 喂 LLM/RAG"、"深抓某站文章列表"、"嫁接海外公司博客热点原文"，或提到 browser-use/Crawl4AI/storage_state/CDP 混合爬取时使用。
---

# hybrid-browser-crawler — browser-use 开锁 × Crawl4AI 规模采集

## 一句话定位

> **browser-use 生产「身份 + 路径」，Crawl4AI 负责「规模化采集与结构化输出」。**
> 不是两个 Agent 一起乱跑——让 browser-use 只啃人类交互难点(登录/弹窗/表单)，啃完导出登录态；
> 真正的批量抓取交给又快又便宜、零 LLM token 的 Crawl4AI。

```
browser_unlock.py  (browser-use)        crawl_pipeline.py  (Crawl4AI)
  login → storage_state.json   ───────►   map  → urls.json
  (登录/弹窗/导航, 解决交互)               crawl → *.md / *.jsonl
                                          (deep crawl / 并发 / schema 抽取)
```

## 环境(已就位)

两库都装在 `cloak-test/.venv`：**browser-use 0.12.9 / crawl4ai 0.8.9**，浏览器内核走系统 Chrome
(`C:\Program Files\Google\Chrome\Application\chrome.exe`，可用环境变量 `HYBRID_CHROME` 覆盖)。
首次若缺 Crawl4AI 内核：`cloak-test/.venv/Scripts/crawl4ai-setup.exe`。

```bash
PY=cloak-test/.venv/Scripts/python.exe
SK=.Codex/skills/hybrid-browser-crawler/scripts
```

## 三段式工作流

### ① login — 开锁(browser-use 产登录态)

```bash
# 手动登录(默认): 弹出有头 Chrome, 你登录/过弹窗, 回车导出 storage_state
$PY $SK/browser_unlock.py login --url "https://target.com/login" --out storage_state.json

# 持久 profile(sessionStorage 依赖的站更稳; 与 storage_state 二选一的更重方案)
$PY $SK/browser_unlock.py login --url "https://target.com/login" \
    --user-data-dir .hybrid_profile --out storage_state.json

# LLM 自动登录(需 ANTHROPIC_API_KEY 或 OPENAI_API_KEY): Agent 自己点
$PY $SK/browser_unlock.py login --url "https://target.com" \
    --task "用账号X密码Y登录并进入订单列表页" --out storage_state.json

# 只起 Chrome 打印 cdp_url(给 crawl --cdp 共享同一浏览器, 调试可见)
$PY $SK/browser_unlock.py cdp --url "https://target.com" --keep
```

### ② map — 发现(Crawl4AI BFS 深抓种子 URL)

```bash
$PY $SK/crawl_pipeline.py map --url "https://target.com/news" --state storage_state.json \
    --max-depth 2 --max-pages 30 --include "/news/,/blog/" --out urls.json
```
- `--include`：路径关键词白名单(逗号分隔)，只留命中的链接，避免深抓失控。
- 产物 `urls.json`：`{"seed":..., "count":N, "urls":[...]}`。

### ③ crawl — 采集(Crawl4AI 并发抓取 → Markdown / JSONL)

```bash
# Markdown(每篇一个 .md, 带 url/title/字数 frontmatter); --fit 开正文剪枝去噪
$PY $SK/crawl_pipeline.py crawl --urls urls.json --state storage_state.json \
    --out youwang/web_sources --fit

# 结构化抽取(给 CSS schema → 出 JSONL, 每行一条记录 + _url)
$PY $SK/crawl_pipeline.py crawl --urls urls.json --state storage_state.json \
    --schema schema.json --out data.jsonl
```
`--urls` 既收 `urls.json`，也收逗号分隔的 URL 串。

## 身份桥接：三选一(默认 storage_state)

`map` / `crawl` 都支持下面三种，按优先级 `--cdp > --user-data-dir > --state`：

| 方式 | 参数 | 适用 | 取舍 |
|---|---|---|---|
| **storage_state**(默认) | `--state storage_state.json` | 多数会员站/SaaS 数据页 | 轻量、可移植；cookie+localStorage 快照 |
| **持久 profile** | `--user-data-dir <dir>` | 依赖 sessionStorage 的站 | 更稳、更真实身份；重、与机器绑定 |
| **共享 CDP** | `--cdp ws://...` | 同一真实浏览器身份、流程复杂、要调试可见 | browser_unlock `cdp` 命令产出端点 |

## 四种混合模式(按场景选)

1. **登录→深扒**：browser-use `login` 导出 `storage_state.json` → Crawl4AI `crawl --state` 进已登录态。后台系统/会员站/SaaS。
2. **共用一个 Chrome(CDP)**：`browser_unlock.py cdp --keep` 拿 `cdp_url` → `crawl --cdp ws://...`。同一真实身份、可视调试。
3. **browser-use 只产种子 URL/路径**：browser-use 找到入口/搜索条件/分页 → 交 `map`/`crawl` 并发抓。列表页/搜索页/文档站/目录。
4. **两阶段 + 兜底**：Crawl4AI 先 `map` 快速发现 → 对高价值 URL `crawl` 出 md/JSON；个别抓不到的页再丢回 browser-use 补救。大站/知识库/官网。

> 原则:**大规模抓取绝不让 browser-use 跑全程**(慢、贵)，它只解决交互难点。

## 排错 / 注意点

- **Git Bash 路径转换坑**(重要)：bash 会把 `/wiki/`、`ws://host/devtools/...` 里的 `/段/` 误转成 Windows 路径
  (实测 `/wiki/` → `D:/Program Files/Git/wiki/`，导致 `--include` 匹配不到、`--cdp` 端点错)。
  传**带斜杠的值**(`--include`、`--cdp`)时前面加 `MSYS_NO_PATHCONV=1`，或 `--include` 用不带前导斜杠的词(如 `news,blog`)。
- **storage_state.json 等于登录凭证**：不能进 git、不能外传。建议放在 `.gitignore` 的目录。
- **sessionStorage 站**：普通 storage_state 可能不够，优先 `--user-data-dir` 持久 profile。
- **深抓失控**：大站务必加 `--max-pages` / `--max-depth` / `--include`，否则爬到天荒地老。
- **手动 login 卡住**：`login` 默认弹有头 Chrome 等你回车——这是交互工具，自动化/无人值守场景用 `--task`(LLM)或先备好 `--user-data-dir` 持久 profile。
- 每站规则/登录方式/分页模式/踩过的坑记到 [reference/HYBRID_CONTEXT.template.md](reference/HYBRID_CONTEXT.template.md) 复制出的副本里，避免重复踩坑。

## 与本仓其它 skill 的关系

- **youwant-hot-topic**：选题侧。它的「海外/网页腿」做"嫁接海外头部公司热点"取原文时，调本 skill 的 `crawl`(公开博客直接抓，登录墙先 `login`)。
- **wechat-channels-pipeline**：抓的是微信视频号(CEF 客户端窗口)，本 skill 抓的是**网页浏览器**，两者不重叠、互补。

## 合规

仅用于已授权账号/公开数据的采集；登录态来自用户本人手动登录；勿外传 `storage_state.json`；遵守目标站 robots 与服务条款。
