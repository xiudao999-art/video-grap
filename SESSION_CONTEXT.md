# Session Context — 快速恢复当前工作状态

> 最后更新: 2026-07-11
> 当前会话主要任务: 歌曲下载 + 设计模板爬取 + 金币/打赏 UI 调研

---

## 一、项目简介

`video-grap` — 视频/音乐/设计素材采集与处理工具集。

核心能力:
- 歌曲批量下载（汽水音乐歌单 → yt-dlp → MP3）
- 设计模板爬取（landing.love / onepagelove / framer / siteinspire）
- 网页混合爬虫（browser-use 登录 + Crawl4AI 规模化采集）
- xrqu 表情/视频素材批量下载
- 抖音视频/音乐下载
- 豆包视觉模型截图分析

---

## 二、当前环境配置

```
项目根目录: D:/video-grap
Python: C:\Users\VAIO\AppData\Local\Programs\Python\Python312\python.exe (3.12)
yt-dlp: C:\Users\VAIO\.local\bin\yt-dlp.exe
Playwright: 全局已安装 + Chromium 浏览器
Crawl4AI: 全局已安装 (0.9.1)
Node.js: 可用
bash: Git Bash (msys2)
OS: Windows 11 Pro
```

### 环境变量
```
TAVILY_API_KEY — 已配置（Tavily搜索API）
ARK_API_KEY — 已配置（豆包视觉模型，火山方舟）
ANTHROPIC_BASE_URL: https://api.deepseek.com/anthropic
```

### Bash 限制（重要）
- Bash 工具网络调用需要 `dangerouslyDisableSandbox: true`
- sandbox 模式会吞掉 stdout，需重定向到 D:/video-grap/.xxx.log
- `/tmp` 是 msys 虚拟目录，Windows Python 读不到
- 控制台编码默认 GBK，中文输出乱码需设置 `PYTHONIOENCODING=utf-8`

---

## 三、当前任务状态

### 任务1: 1000首歌曲下载 ✅ 部分完成

**进度**: 218/1000 首已下载
**输出目录**: `D:/video-grap/Downloaded/music_batch/`
**文件格式**: `{序号:04d}_{歌名}_{歌手}.mp3`

**已生成文件**:
- `汽水音乐歌单.md` — 1000首可用歌曲列表
- `Downloaded/music_batch/download_plan.md` — 下载方案（免费平台+URL）
- `Downloaded/music_batch/summary.md` — 完成报告
- `Downloaded/music_batch/_final_summary.json` — 详细统计

**继续下载**:
```bash
cd D:/video-grap
python tools/download_all_1000.py     # 断点续传，自动跳过已下载
# 或双击 tools/continue_download.bat
```

**数据来源**: `汽水音乐丨版权禁投+可用歌单 副本.xlsx` → `Downloaded/qishui_music_song_list.json`

### 任务2: 设计模板调研 ✅ 已完成

**已爬取网站**: landing.love (817 URLs) / onepagelove (1558) / framer (451) / siteinspire (1324)

**可下载模板清单**:
- `Downloaded/design_crawls/top30_downloadable_templates_final.md` — 30个可下载模板链接
- `Downloaded/design_crawls/all_usable_templates_summary.md` — 汇总
- `Downloaded/design_crawls/coin_reward_ui_research_report.md` — 金币/打赏 UI 调研

**可直接使用的模板**:
- NEONYX (Framer 免费): https://www.framer.com/community/marketplace/templates/neonyx/
- Crafto Music ($16): https://onepagelove.com/crafto-music
- Watch Party (免费): https://onepagelove.com/watch-party
- LaunchFolio (Framer 免费): https://www.framer.com/community/marketplace/templates/launchnow/

**Deep Research 结论**（金币+美女+歌曲视觉方案）:
- 暗黑沉浸式背景 + 金色财富元素 + 霓虹娱乐强调色
- 配色: 深紫/深蓝底 + 金色 #FFD700 + 霓虹紫 #b026ff + 玫红 #ff2d7a
- 金币: 3D旋转金币 / 发光token / 粒子爆开动效
- 礼物: 紫色sparkle标记互动礼物 / 高价值礼物全屏特效
- 参考: Twitch Bits 宝石图标 / YouTube Jewels-Rubies兑换 / Streamlabs 金额分级Alert

---

## 四、关键脚本索引

| 脚本 | 用途 |
|------|------|
| `tools/crawl_pipeline.py` | Crawl4AI 爬取管道 (map发现 + crawl抓取 + preset预设) |
| `tools/browser_unlock.py` | browser-use 登录/导出 storage_state |
| `tools/download_all_1000.py` | 1000首歌批量下载(断点续传) |
| `tools/download_batch.py` | 按范围批次下载歌曲 |
| `tools/see_screen.py` | 截图 → 豆包视觉模型文字描述 |
| `tools/xrqu_download.py` | xrqu 表情图片批量下载(8线程) |
| `tools/xrqu_video_batch.py` | xrqu 视频预览批量下载 |
| `tools/aigei_set_covers.py` | aigei.com 封面图 Playwright截图 |
| `tools/screenshot_templates.py` | 批量截图模板页面 |
| `tools/explore_template_usage.py` | 探索模板下载/购买方式 |
| `tools/batch_download_1000_songs.py` | 歌曲下载(旧版,10首测试用) |

---

## 五、常用命令速查

### 爬取设计网站
```bash
python tools/crawl_pipeline.py preset landing-love    # 发现链接
python tools/crawl_pipeline.py preset onepagelove
python tools/crawl_pipeline.py preset framer-templates
python tools/crawl_pipeline.py preset siteinspire

python tools/crawl_pipeline.py crawl --urls urls/xxx.json --out xxx --fit  # 抓取Markdown
```

### 歌曲下载
```bash
python tools/download_all_1000.py           # 全量下载
python tools/download_batch.py 200 300     # 下载200-300
```

### 截图分析
```bash
python tools/see_screen.py                          # 截全屏分析
python tools/see_screen.py -i "image.png" -q "问题"  # 分析指定图片
```

### Tavily 搜索（Bash不可用时用）
```bash
# 见 CLAUDE.md 中的 "REST API 直调" 方法
# curl → /tmp → cp 到 D:/video-grap/.xxx.json → Read
```

---

## 六、目录结构速览

```
D:/video-grap/
├── tools/              ← 所有脚本（66文件, 31个提交到git）
├── hybrid-browser-crawler/  ← 混合爬虫 Skill
├── .claude/            ← Claude Code skills配置
├── Downloaded/
│   ├── music_batch/    ← 218首MP3 + 下载报告
│   ├── design_crawls/  ← 设计模板截图/URL/报告
│   ├── templates/      ← 模板截图(13站点)
│   └── xrqu_表情/视频   ← 素材下载
├── config/             ← cookies/token (gitignored)
├── douyin-downloader/  ← 抖音下载引擎 (gitignored)
├── video/              ← 视频素材 (gitignored)
├── CLAUDE.md           ← 项目规则
├── SESSION_CONTEXT.md  ← 本文件
└── 汽水音乐歌单.md      ← 1000首可用歌单
```

## 七、Git 状态

- **仓库**: https://github.com/xiudao999-art/video-grap
- **已提交**: 31个代码/配置文件
- **已排除**: Downloaded/ config/ douyin-downloader/ video/ tmp/ *.xlsx *.mp3
- 资源文件全部保留本地，不随 git 提交

---

## 八、恢复会话建议

在新的 Claude Code 会话中，打开此文件后可以：
1. 检查 `CLAUDE.md` 了解环境限制
2. 读取 `Downloaded/music_batch/summary.md` 了解下载进度
3. 运行 `python tools/download_all_1000.py` 继续下载歌曲
4. 读取 `Downloaded/design_crawls/` 下的报告了解模板调研结果
