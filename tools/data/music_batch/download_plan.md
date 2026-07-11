# 1000首歌曲下载方案

> 基于 Tavily 调研结果整理（3轮搜索，30+个结果）
> 来源：汽水音乐 ✅可用歌单

---

## 一、免费下载平台汇总

### A. 可以直接搜索下载的（优先级1）

| 平台 | 方式 | 说明 |
|------|------|------|
| **MP3Juice** | 搜索歌名/歌手 → 直接下载MP3 | 免费无注册，320kbps |
| **YTMP3 / Y2Mate** | YouTube链接 → MP3 | 配合yt-dlp使用 |
| **yt-dlp** | `ytsearch:歌名 歌手` → MP3 | 最可靠，已安装在本地 |

### B. 免费合法音乐库（优先级2）

| 平台 | URL | 说明 |
|------|-----|------|
| **Internet Archive** | archive.org/details/audio | 公开领域音乐存档 |
| **SoundCloud** | soundcloud.com | 部分歌曲提供免费下载 |
| **Free Music Archive** | freemusicarchive.org | Creative Commons 音乐 |
| **Jamendo** | jamendo.com | 独立音乐人 |

### C. 中文音乐论坛/博客（优先级3）

| 平台 | URL | 说明 |
|------|-----|------|
| **BesGold** | bbs.besgold.com | 中文音乐论坛，需注册 |
| **MP3-Mandarin** | mp3-mandarin.blogspot.com | 中文歌曲博客 |
| **XiaLaLa** | xialala.com | 音乐分享 |

### D. 汽水/抖音直接下载（优先级1）

| 平台 | 方式 |
|------|------|
| **汽水音乐/抖音** | douyin-downloader 引擎下载 |

---

## 二、每首歌的下载策略

对每首歌，按以下顺序尝试：

```
方案1: yt-dlp ytsearch:"{歌名} {歌手}" 
   → 下载YouTube上最匹配的音频为MP3
   
方案2: MP3Juice 搜索 "{歌名} {歌手}"
   → 直接在MP3Juice搜索并下载MP3
   
方案3: Internet Archive / SoundCloud 搜索
   → 搜索公开/免费歌曲
   
方案4: 汽水音乐原平台（如有链接）
   → douyin-downloader下载
```

---

## 三、Agent分配

10个 agent，各负责100首：

| Agent | 歌曲范围 (#) |
|-------|-------------|
| song-downloader-01 | 001-100 |
| song-downloader-02 | 101-200 |
| song-downloader-03 | 201-300 |
| song-downloader-04 | 301-400 |
| song-downloader-05 | 401-500 |
| song-downloader-06 | 501-600 |
| song-downloader-07 | 601-700 |
| song-downloader-08 | 701-800 |
| song-downloader-09 | 801-900 |
| song-downloader-10 | 901-1000 |

---

## 四、下载命令模板

```bash
# 方案1: yt-dlp
yt-dlp -x --audio-format mp3 --audio-quality 0 \
  -o "D:/video-grap/Downloaded/music_batch/%(title)s.%(ext)s" \
  "ytsearch:歌名 歌手"

# 方案2: MP3Juice (Playwright自动化)
# 打开 mp3juice, 搜索歌名, 点击下载

# 方案3: Internet Archive
yt-dlp "https://archive.org/search?query=歌名+歌手"
```

## 五、文件命名规则

`{0001-1000}_{歌名}_{歌手}.mp3`

## 六、输出

- 成功歌曲：D:/video-grap/Downloaded/music_batch/
- 失败报告：D:/video-grap/Downloaded/music_batch/summary.md
