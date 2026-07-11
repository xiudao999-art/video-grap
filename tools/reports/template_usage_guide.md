# 20 个模板下载/使用方式探索报告

## 一、重要结论

用 hybrid-browser-crawler（Crawl4AI）扫描后，20 个模板可分为两类：

| 类型 | 数量 | 代表 | 使用方式 |
|------|------|------|---------|
| **可直接使用/购买的模板** | 3 | Framer Marketplace 模板 | 免费复制或付费购买 |
| **仅可作参考的灵感作品** | 17 | landing.love / SiteInspire / One Page Love 收录页 | 访问实际网站，截图/学习，手动复刻 |

> ⚠️ **设计灵感站（landing.love / SiteInspire / One Page Love）本身不卖模板**，它们只是展示优秀网站作品。页面上的 "Visit Site" 链接指向的是别人的实际网站，不是可下载的模板文件。

---

## 二、可直接使用/购买的模板

### 1. LaunchNow / LaunchFolio（Framer）— **免费**
- **页面**: https://www.framer.com/community/marketplace/templates/launchnow/
- **Live Preview**: https://launchfolio.framer.website/
- **使用方式**: 点击 **"Use for Free"** → 复制到你的 Framer 账户
- **价格**: 免费
- **适用**: 产品发布/上线页，可改造成活动发布/主播上线预告

### 2. NightSec（Framer）— **$79**
- **页面**: https://www.framer.com/community/marketplace/templates/nightsec/
- **使用方式**: 点击 **"Buy for $79"** 购买后复制使用
- **价格**: $79
- **适用**: 暗色 SaaS/科技风，适合夜店/安全/科技感的娱乐平台

### 3. Salesfllow（Framer）— **$49**
- **页面**: https://www.framer.com/community/marketplace/templates/salesfllow/
- **使用方式**: 点击 **"Buy for $49"** 购买后复制使用
- **价格**: $49
- **适用**: 销售/转化 funnel，适合充值/打赏/会员转化页

---

## 三、仅可作参考的灵感作品（17 个）

这些页面都有 **"Visit Site"** 按钮，链接到实际网站。你可以：
1. 打开实际网站截图保存
2. 用浏览器开发者工具（F12）查看 CSS/HTML 结构
3. 学习配色、布局、动效、字体
4. 在 Framer/Webflow/代码中手动复刻

### landing.love 收录的实际网站

| 模板 | landing.love 页面 | 实际网站 | 参考价值 |
|------|------------------|---------|---------|
| Bored Ape Yacht Club | https://www.landing.love/sites/boredapeyachtclub/ | https://boredapeyachtclub.com/ | NFT/加密社区/游戏感 |
| BitcoinOS | https://www.landing.love/sites/bitcoinos/ | https://bitcoinos.build/ | 比特币/加密操作系统，金币质感 |
| SHAPESHIFT Festival | https://www.landing.love/sites/shapeshiftfestival/ | https://shapeshiftfestival.com/ | 音乐节，霓虹派对氛围 |
| DAYDREAM Player | https://www.landing.love/sites/daydreamplayer/ | https://www.daydreamplayer.com/ | 音乐播放器，沉浸式暗色 |
| Playfight | https://www.landing.love/sites/letsplayfight/ | https://www.letsplayfight.com/ | 游戏/竞技感 |
| FAT FAT FAT Festival | https://www.landing.love/sites/fatfatfatfestival/ | https://www.fatfatfatfestival.it/2019 | 音乐节 |
| Joondalup Festival | https://www.landing.love/sites/joondalupfestival/ | https://joondalupfestival.com.au/ | 艺术节/活动 |
| Rodeo Club | https://www.landing.love/sites/rodeo-club/ | https://rodeo.club/ | Club/夜店感 |
| Double Play | https://www.landing.love/sites/doubleplay/ | https://www.doubleplay.studio | 游戏/双重玩法 |

### SiteInspire 收录的实际网站

| 模板 | SiteInspire 页面 | 实际网站 | 参考价值 |
|------|-----------------|---------|---------|
| Players Paris | https://www.siteinspire.com/website/9127-players-paris | http://www.playersparis.tv/ | 玩家/娱乐品牌 |
| Arcade Edit | https://www.siteinspire.com/website/11791-arcade-edit | https://arcadeedit.com/ | 街机/游戏感 |
| Paper Triangles | https://www.siteinspire.com/website/12138-paper-triangles | https://www.papertriangles.com/ | 创意机构 |
| Field Day Festival 2024 | https://www.siteinspire.com/website/12559-field-day-festival-2024 | https://fielddayfestivals.com/ | 音乐节 |
| Click Therapeutics | https://www.siteinspire.com/website/13169-click-therapeutics | https://www.clicktherapeutics.com/ | 数字健康/游戏化（Squarespace） |
| Knight Associates | https://www.siteinspire.com/website/8247-knight-associates | https://knightassociates.co.nz/ | 骑士/游戏化品牌感 |
| Extended Play | https://www.siteinspire.com/website/7003-extended-play | http://www.extendedplay.nyc/ | 音乐/播放 |

### One Page Love 收录的实际网站

| 模板 | One Page Love 页面 | 实际网站 | 参考价值 |
|------|-------------------|---------|---------|
| Arcade Labs | https://onepagelove.com/arcade-labs | https://arcade.la/ | 街机/游戏实验室 |

---

## 四、如何使用 hybrid-browser-crawler 批量获取这些资源

### 步骤 1：批量截图实际网站

```bash
python tools/crawl_pipeline.py crawl \
  --urls "D:/video-grap/Downloaded/design_crawls/urls/top20_coin_reward_templates.json" \
  --out coin_reward_references --fit
```

### 步骤 2：提取实际网站链接

已用 `tools/explore_template_usage.py` 完成，结果保存在：
`D:\video-grap\Downloaded\design_crawls\exploration\template_usage_exploration_report.json`

### 步骤 3：批量截图实际网站（而非平台展示页）

可以基于 exploration report 中的 external_links 做第二轮截图：

```python
# 读取 report 中的 Visit Site 链接
# 用 screenshot_templates.py 的逻辑批量截图
```

### 步骤 4：Framer 模板直接使用

对于 Framer 模板：
1. 登录 Framer 账户
2. 打开模板页面
3. 点击 "Use for Free" 或 "Buy"
4. 复制到你自己的 Framer 项目
5. 修改内容、配色、图片

---

## 五、实际可操作建议

### 方案 A：最快落地（推荐）
1. **免费使用 LaunchFolio 模板** 作为基础框架
2. 参考 **BitcoinOS** 的金币/加密视觉质感
3. 参考 **SHAPESHIFT Festival / Rodeo Club** 的夜店/派对氛围
4. 参考 **Bored Ape Yacht Club** 的社区/游戏化元素
5. 在 Framer 中直接修改成「金币+美女+歌曲」主题

### 方案 B：完全自定义
1. 用 **Figma** 或 **Framer** 新建项目
2. 把上面 17 个参考网站的截图作为 mood board
3. 手动复刻喜欢的模块和动效
4. 自己写代码实现或用 Framer 无代码搭建

### 方案 C：购买高级模板
1. 购买 **NightSec（$79）** 或 **Salesfllow（$49）**
2. 在 Framer 中二次开发
3. 替换视觉元素为主播/金币/音乐主题

---

## 六、各平台模板获取特点

| 平台 | 是否有模板下载 | 获取方式 |
|------|---------------|---------|
| **landing.love** | ❌ 无 | 只看灵感，访问实际网站 |
| **SiteInspire** | ❌ 无 | 只看灵感，访问实际网站 |
| **One Page Love** | ⚠️ 部分有 | 详情页可能有 "Buy Template" 或外部购买链接 |
| **Framer Marketplace** | ✅ 有 | 免费复制或付费购买，直接可用 |

---

*报告生成时间：2026-07-09*
*探索脚本：D:\video-grap\tools\explore_template_usage.py*
