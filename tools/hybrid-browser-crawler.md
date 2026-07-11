---
name: hybrid-browser-crawler
version: 2.0
---

# hybrid-browser-crawler — 浏览器混合爬虫（项目适配版）

> **browser-use 开锁 × Crawl4AI 规模采集**
> 
> 本项目适配版本，专为设计灵感网站（landing.love, onepagelove, framer, siteinspire）优化

## 目录结构

```
D:/video-grap/
├── tools/
│   ├── browser_unlock.py          # 登录/解锁脚本
│   ├── crawl_pipeline.py          # 爬取管道脚本
│   └── schemas/
│       └── design_template.json   # 设计模板提取 schema
└── Downloaded/design_crawls/      # 输出目录
    ├── storage_states/            # 登录态文件
    ├── urls/                      # 发现的 URL 列表
    ├── content/                   # Markdown 内容
    └── data/                      # 结构化 JSON 数据
```

## 快速开始

### 1. 使用预设配置爬取设计网站

```bash
# 爬取 landing.love
python tools/crawl_pipeline.py preset landing-love

# 爬取 onepagelove
python tools/crawl_pipeline.py preset onepagelove

# 爬取 framer templates
python tools/crawl_pipeline.py preset framer-templates

# 爬取 siteinspire
python tools/crawl_pipeline.py preset siteinspire
```

### 2. 手动指定 URL 爬取

```bash
# 发现链接
python tools/crawl_pipeline.py map --url "https://landing.love" \
    --max-depth 2 --max-pages 50 --out urls/landing_love.json

# 爬取为 Markdown
python tools/crawl_pipeline.py crawl --urls urls/landing_love.json \
    --out content/landing_love --fit

# 结构化提取（使用 CSS schema）
python tools/crawl_pipeline.py crawl --urls urls/landing_love.json \
    --schema schemas/design_template.json --out data/landing_love.jsonl
```

### 3. 需要登录的网站

```bash
# 手动登录并保存登录态
python tools/browser_unlock.py login --url "https://example.com/login" \
    --out storage_states/example.json

# 使用登录态爬取
python tools/crawl_pipeline.py map --url "https://example.com" \
    --state storage_states/example.json --out urls/example.json
```

## 预设配置

| 预设名称 | 网站 | 描述 |
|---------|------|------|
| `landing-love` | landing.love | Landing page 设计画廊 |
| `onepagelove` | onepagelove.com | 单页网站灵感 |
| `framer-templates` | framer.com/templates | Framer 模板市场 |
| `siteinspire` | siteinspire.com | 网页设计灵感库 |

## 命令参考

### browser_unlock.py

```bash
# 手动登录
python tools/browser_unlock.py login --url "<登录页URL>" --out <文件名.json>

# LLM 自动登录（需设置 ANTHROPIC_API_KEY 或 OPENAI_API_KEY）
python tools/browser_unlock.py login --url "<URL>" \
    --task "用账号密码登录" --out <文件名.json>

# 启动共享 Chrome（CDP 模式）
python tools/browser_unlock.py cdp --url "<URL>" --keep
```

### crawl_pipeline.py

```bash
# map - 发现链接
python tools/crawl_pipeline.py map --url "<URL>" [选项]
  --max-depth <N>      # 最大爬取深度（默认：2）
  --max-pages <N>      # 最大页面数（默认：30）
  --include "<模式>"   # URL 路径白名单（逗号分隔）
  --out <文件名>       # 输出文件名
  --state <文件.json>  # 使用登录态

# crawl - 爬取内容
python tools/crawl_pipeline.py crawl --urls <来源> [选项]
  --urls <来源>        # urls.json 文件或逗号分隔的 URL
  --out <目录/文件>    # 输出目录（Markdown）或文件（JSONL）
  --schema <文件.json> # CSS 提取 schema（输出 JSONL）
  --fit                # 启用内容剪枝（更干净的正文）
  --state <文件.json>  # 使用登录态

# preset - 使用预设配置
python tools/crawl_pipeline.py preset <预设名>
  可用预设：landing-love, onepagelove, framer-templates, siteinspire
```

## 输出格式

### Markdown 输出

每个页面保存为一个 `.md` 文件，包含 frontmatter：

```markdown
---
url: https://example.com/page
title: Page Title
md_chars: 1523
---

[页面正文内容...]
```

### JSONL 输出

每行一个 JSON 对象，包含提取的字段：

```json
{"title": "Template Name", "designer": "John Doe", "images": [...], "_url": "https://..."}
{"title": "Another Template", "designer": "Jane Smith", "images": [...], "_url": "https://..."}
```

## 注意事项

1. **路径问题**：Git Bash 会自动转换 `/` 路径，使用 `--include` 时建议用 `MSYS_NO_PATHCONV=1` 前缀
2. **登录态安全**：`storage_states/*.json` 包含敏感信息，**不要提交到 git**
3. **爬取频率**：建议添加适当的延迟，避免对目标网站造成压力
4. **Robots.txt**：遵守目标网站的 robots.txt 和服务条款

## 依赖

- Python 3.12+
- browser-use
- crawl4ai
- Playwright（已安装）

## 故障排除

### Crawl4AI 内核未安装

```bash
crawl4ai-setup
```

### Chrome 路径错误

设置环境变量：
```bash
set HYBRID_CHROME=C:\Path\To\chrome.exe
```

### 中文显示乱码

已配置 `sys.stdout` 使用 UTF-8 编码，Windows 控制台可能需要设置为 UTF-8：
```bash
chcp 65001
```
