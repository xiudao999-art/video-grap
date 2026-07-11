# HYBRID_CONTEXT — <目标站名>

> 每抓一个新站，复制本模板到 `youwang/_hybrid_<站名>.md`，把踩过的坑记下来，避免重复试错。
> 本文件是「站点作战手册」，不是凭证仓库——**不要把 storage_state.json / 密码写进来**。

## 基本信息
- 目标站：`https://...`
- 入口/登录页：`https://.../login`
- 采集目标：<要什么数据，列表页还是详情页，字段有哪些>

## 身份方式
- [ ] storage_state（默认）：`--state storage_state.json`
- [ ] 持久 profile（sessionStorage 依赖时）：`--user-data-dir .hybrid_profile`
- [ ] 共享 CDP：`--cdp ws://...`
- 登录方式：<手动 / LLM --task / 短信验证码 / OAuth…>
- 登录态有效期：<多久过期，需多久重登一次>

## 路径/分页规则
- 文章 URL 形如：`/news/<slug>` → `--include "news"`（注意 Git Bash 路径坑，别带前导斜杠或加 `MSYS_NO_PATHCONV=1`）
- 列表分页：<?page=N / 无限滚动 / "加载更多"按钮>
- 深抓参数建议：`--max-depth <?> --max-pages <?>`

## CSS schema（结构化抽取时）
```json
{
  "name": "<记录名>",
  "baseSelector": "<每条记录的容器选择器>",
  "fields": [
    {"name": "title", "selector": "<...>", "type": "text"},
    {"name": "link",  "selector": "<...>", "type": "attribute", "attribute": "href"}
  ]
}
```

## 跑通的命令(可直接复用)
```bash
PY=cloak-test/.venv/Scripts/python.exe
SK=.claude/skills/hybrid-browser-crawler/scripts
# 1) 登录
$PY $SK/browser_unlock.py login --url "..." --out storage_state.json
# 2) 发现
MSYS_NO_PATHCONV=1 $PY $SK/crawl_pipeline.py map --url "..." --state storage_state.json --include "..." --out urls.json
# 3) 采集
$PY $SK/crawl_pipeline.py crawl --urls urls.json --state storage_state.json --out ... [--fit | --schema schema.json]
```

## 踩过的坑 / 失败页
- <哪些页面抓不到，为什么，怎么绕(改 user_data_dir? 丢回 browser-use 补救?)>
- <反爬/限频/验证码 触发条件与规避>
