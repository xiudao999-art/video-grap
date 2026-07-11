# 项目规则 (CLAUDE.md)

## ⚠️ 当前模型不支持图片输入（重要）

本机 Claude Code 配置的模型（Fireworks GLM 路由，见 `~/.claude/settings.json`）是**纯文本模型**。
任何返回图片的工具结果都会污染会话历史，导致后续所有请求报
`API Error: 400 This model does not support image inputs`，且无法自愈（图片留在上下文里）。

规则：
- **禁止**调用 `mcp__windows-mcp__Screenshot`（settings.json 已加 deny，双保险）。
- 不要用 Read 工具读取 png/jpg 等图片文件。
- 如果会话已经混入图片报 400：该会话历史已损坏，按两次 Esc 回退到截图之前的消息重试，
  或直接开新会话（`/compact` 也会失败，因为压缩时同样要把图片发给模型）。

## ⚠️ 上下文超限死循环（`token limit exceeded` 系列报错）

**背景（当前已不适用，仅存档）**：之前接的 Kimi K2.7 系列硬上下文窗口是 262144 tokens（256K），超过就
400 拒绝，且一旦超限无法自愈——自动压缩/手动 `/compact` 都要先把全部历史打包发一次做摘要，这次打包本身
也会超限，于是死循环报错（报错里的 token 数会一点点往上爬，就是死循环证据，和截图 400 是同一种坑）。

**当前（2026-07-11 起）**：模型已切换到 DeepSeek（见下方"当前模型配置"），V4 Pro / V4 Flash 原生支持
**100 万（1,000,000）tokens** 上下文窗口，比 Kimi 宽松得多，正常使用基本不会撞到。已在
`~/.claude/settings.json` 设置 `CLAUDE_CODE_MAX_CONTEXT_TOKENS: "1000000"`，让 Claude Code 按真实
窗口大小提前自动压缩。

如果哪天换了别的第三方模型（通过 `ANTHROPIC_BASE_URL` 接入、Claude Code 不认识的模型名），一定要记得
同步查一下它的真实上下文窗口大小，更新这个变量，否则会重复这个死循环坑。

真超限卡死时的恢复办法（只能事后补救，没法自动恢复）：
1. 连按两次 `Esc` 回退到对话暴增之前的那条消息，再继续；
2. 或者直接开新会话（旧会话的活儿如果是写文件之类，检查一下文件当时写到哪儿了再继续）。

容易触发的场景：整段网页 HTML / 大量爬虫抓取结果 / 大文件内容直接塞进对话（而不是让 agent 自己读文件分段处理）。
下次做类似"抓取模板市场""扒网页"这种任务，提示 agent 分批处理、避免一次性把整页 HTML 贴进上下文。

## 当前模型配置（2026-07-11 起）

Claude Code 整体切到了 **DeepSeek**（不再用 Kimi/Moonshot）：
- `ANTHROPIC_BASE_URL`: `https://api.deepseek.com/anthropic`（DeepSeek 的 Anthropic 兼容端点）
- 主模型（opus/sonnet 别名）: `deepseek-v4-pro`
- haiku 别名（快速/后台任务）: `deepseek-v4-flash`
- 备用（`fallbackModel`，主模型过载/不可用时自动切换）: `deepseek-v4-flash`
- 不需要像 Kimi 那样强制加 `thinking` 参数，DeepSeek 默认自己判断要不要思考，实测过不传也不报错。
- `deepseek-chat` / `deepseek-reasoner` 这两个旧模型名会在 2026/07/24 弃用，别再用了，统一用
  `deepseek-v4-pro` / `deepseek-v4-flash`。

### 需要"看屏幕/看图片"时 → 用豆包视觉模型代看

已备好脚本 `D:/video-grap/tools/see_screen.py`（已测试可用）：截屏（或读指定图片/图片URL）→
发给**豆包 Doubao Seed 2.1 Pro**（火山方舟 Responses API，`/api/v3/responses`，
模型 `doubao-seed-2-1-pro-260628`，支持视觉）→ stdout 输出纯文字描述。
主模型只读文字，图片永远不进上下文。

```bash
# 描述当前屏幕（默认问法：前台窗口、弹窗/二维码/报错等）
python D:/video-grap/tools/see_screen.py

# 带具体问题
python D:/video-grap/tools/see_screen.py -q "抖音登录二维码出现了吗？"

# 解析已有图片文件（本地路径或 http(s) URL 均可）
python D:/video-grap/tools/see_screen.py -i "D:/path/xx.png"
python D:/video-grap/tools/see_screen.py -i "https://example.com/xx.png"
```

注意：
- 用**全局 python**（3.12，已有 pillow+requests），不要用 douyin-downloader 的 venv。
- ⚠️ **PowerShell 中文控制台编码坑**：直接跑会因为控制台默认 GBK 而把中文输出显示成乱码
  （API 本身是对的，只是显示层坏了）。用 Bash 工具跑之前先执行一次：
  `chcp 65001 | Out-Null; [Console]::OutputEncoding = [System.Text.Encoding]::UTF8`，
  或者把输出重定向到文件后用 Read 工具读取（更稳）。
- 走网络，若 Bash 沙箱阻断网络需要 `dangerouslyDisableSandbox: true`。
- 依赖环境变量 `ARK_API_KEY`（已通过 `setx` 持久化到当前用户环境变量，新开的终端都能读到）。
- 只要 UI 元素坐标（点按钮用）而不需要视觉判断时，仍可用
  `mcp__windows-mcp__Snapshot`（保持 `use_vision=false` 默认值），它返回纯文本 UI 树。

## Tavily 搜索使用方法（已验证可用）

本项目已安装 Tavily MCP（见 `~/.claude.json` 项目级配置）：
```
tavily: npx -y tavily-mcp@latest   (stdio, env TAVILY_API_KEY 已配置)
```
`claude mcp list` 显示 `✓ Connected`。API key 已通过 REST API 实测返回 HTTP 200。

### 两种调用方式

**1. MCP 工具（首选，会话重启后可用）**
重启 Claude Code 会话后，Tavily 工具会以 `mcp__tavily__*` 形式加载（如 `tavily-search`、`tavily-extract`）。
直接调用即可，无需手动处理网络/沙箱。

**2. REST API 直调（当前会话 MCP 工具未加载时用）**

⚠️ 本环境已知坑：
- Bash 工具默认沙箱**会阻断网络**，curl 不返回内容。
- 给 Bash 加 `dangerouslyDisableSandbox: true` 后网络通，**但该 flag 会把 stdout 整个吞掉**（命令确实执行了，只是看不到输出）。
- `/tmp` 是 msys 挂载路径，Windows 的 Read 工具和 `python` 访问不到，只有 bash 内置命令能看到。

**因此可用的稳定模式 = 「沙箱外跑 curl 写文件 → 复制到项目目录 → 用 Read 读取」：**

```bash
# 第一步：dangerouslyDisableSandbox: true，写到一个 bash 能看到的临时路径
curl -sS -X POST https://api.tavily.com/search \
  -H "Content-Type: application/json" \
  -d '{"api_key":"'"$TAVILY_API_KEY"'","query":"<query>","max_results":8,"include_answer":true}' \
  -o /tmp/tav_out.json

# 第二步：不用 sandbox flag，复制到项目内 Windows 可见路径
cp /tmp/tav_out.json "D:/video-grap/.tav_out.json"
```
然后用 Read 工具读 `D:\video-grap\.tav_out.json`。

注意：第一步的 Bash 调用会显示「no output」——这是正常的，不要误判为失败，去读文件即可。

### 端点参考
- 搜索：`POST https://api.tavily.com/search`，body `{api_key, query, max_results, include_answer}`
- 抽取网页正文：`POST https://api.tavily.com/extract`，body `{api_key, urls}`
- key 在环境变量 `TAVILY_API_KEY`（也已写进 MCP env）。

### 清理
`.tav_out.json` 是临时搜索结果缓存，用完可删，不要提交到 git。

## 抖音视频下载（jiji262/douyin-downloader v2.0.0）

已安装在本项目 `D:/video-grap/douyin-downloader`，配好 venv + Playwright chromium + config.yml。
有专门的 skill：`.claude/skills/douyin-download/SKILL.md` —— 下载抖音内容时按那个 skill 走。

要点：
- 入口：`D:/video-grap/douyin-downloader/.venv/Scripts/python.exe run.py`（不要用全局 python）
- 首次使用要先登录拿 cookie：跑一次下载触发自动登录，或 `python tools/cookie_fetcher.py`；cookie 存 `config/cookies.json`（gitignored）
- 下载走网络，Bash 调用要 `dangerouslyDisableSandbox: true` 并把输出重定向到 `D:/video-grap/.run.log` 再 Read（同上 Tavily 的坑）
- 反封策略已默认开好（限速 + 退避 + 浏览器回退），别调高 `thread`、别关 `browser_fallback`
