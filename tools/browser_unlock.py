#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
browser_unlock.py — 混合打法第 1 层「开锁」：用 browser-use 解决人类交互难点
(登录 / 弹窗 / 复杂表单 / 导航), 把已登录态导出成 storage_state.json，交给
crawl_pipeline.py(Crawl4AI) 做规模化采集。

【本项目适配版】
- 使用全局 Python 3.12
- 输出目录: D:/video-grap/Downloaded/design_crawls/storage_states/
- 支持设计网站专用配置

设计原则：browser-use 只负责"生产身份和路径"，**不跑全程**(它慢、贵)。

两种登录模式：
  --manual (默认)  : 打开有头 Chrome → 导航到登录页 → 你手动登录 → 回车 → 导出 storage_state
  --task "..."     : 有 LLM key 时，browser-use Agent 自动完成登录任务，再导出 storage_state

两种身份载体(对应 crawl_pipeline 的 --state / --user-data-dir)：
  storage_state.json (默认, 轻量可移植)   ←  --out storage_state.json
  持久 user_data_dir (sessionStorage 依赖的站更稳) ← --user-data-dir <dir>

用法：
  # 手动登录导出登录态
  python tools/browser_unlock.py login --url "https://target.com/login" --out storage_states/example.json
  # 持久 profile(更稳, 适合 sessionStorage 站)
  python tools/browser_unlock.py login --url "https://target.com/login" --user-data-dir .hybrid_profile --out storage_states/example.json
  # LLM 自动登录(需 ANTHROPIC_API_KEY 或 OPENAI_API_KEY)
  python tools/browser_unlock.py login --url "https://target.com" --task "用账号X密码Y登录并进入订单页" --out storage_states/example.json
  # 只启动 Chrome 暴露 CDP(给 crawl_pipeline --cdp 共享同一浏览器)
  python tools/browser_unlock.py cdp --url "https://target.com" --keep
"""
import os, sys, io, json, asyncio, argparse
from pathlib import Path

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass

# 项目配置
PROJECT_ROOT = Path("D:/video-grap")
STORAGE_DIR = PROJECT_ROOT / "Downloaded" / "design_crawls" / "storage_states"
DEFAULT_CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
CHROME = os.environ.get("HYBRID_CHROME", DEFAULT_CHROME)

try:
    from browser_use import Browser
except ImportError:
    sys.exit("ERROR: 未安装 browser-use。请运行: pip install browser-use")


def _make_browser(headless, user_data_dir=None, storage_state=None, keep_alive=True):
    kw = dict(executable_path=CHROME, headless=headless, keep_alive=keep_alive)
    if user_data_dir:
        kw["user_data_dir"] = os.path.abspath(user_data_dir)
    if storage_state and os.path.exists(storage_state):
        kw["storage_state"] = os.path.abspath(storage_state)
    return Browser(**kw)


async def _wait_enter(prompt):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, input, prompt)


async def cmd_login(args):
    use_llm = bool(args.task) and (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY"))
    headless = False
    browser = _make_browser(headless=headless, user_data_dir=args.user_data_dir)
    print(f"[login] 启动 Chrome (headful{' + 持久profile' if args.user_data_dir else ''}) ...")
    await browser.start()
    if args.url:
        print(f"[login] 导航到 {args.url}")
        await browser.navigate_to(args.url)

    if use_llm:
        print(f"[login] LLM 模式: Agent 执行任务 → {args.task}")
        from browser_use import Agent
        if os.environ.get("ANTHROPIC_API_KEY"):
            from browser_use import ChatAnthropic as Chat
            llm = Chat(model="claude-sonnet-4-6")
        else:
            from browser_use import ChatOpenAI as Chat
            llm = Chat(model="gpt-4o")
        agent = Agent(task=args.task, llm=llm, browser=browser)
        await agent.run(max_steps=args.max_steps)
    else:
        if args.task:
            print("[login] ⚠️ 给了 --task 但没有 LLM key, 退回手动模式")
        print("\n  >>> 请在弹出的 Chrome 里手动完成登录 / 过弹窗 / 导航到目标页 <<<")
        await _wait_enter("  登录完成后回到这里按 Enter 导出登录态... ")

    # 确保输出目录存在
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    out_path = STORAGE_DIR / args.out if not os.path.isabs(args.out) else Path(args.out)

    # 导出 storage_state
    state = await browser.export_storage_state(str(out_path))
    n_cookies = len(state.get("cookies", [])) if isinstance(state, dict) else "?"
    print(f"[login] ✓ 已导出 storage_state → {out_path}  (cookies: {n_cookies})")
    if args.user_data_dir:
        print(f"[login] ✓ 持久 profile 保留在 → {os.path.abspath(args.user_data_dir)}")
    await browser.kill()
    print("VERIFY_UNLOCK: PASS")


async def cmd_cdp(args):
    """只启动 Chrome 并打印 cdp_url, 供 crawl_pipeline --cdp 共享同一浏览器。"""
    browser = _make_browser(headless=args.headless, user_data_dir=args.user_data_dir)
    await browser.start()
    if args.url:
        await browser.navigate_to(args.url)
    print(json.dumps({"cdp_url": browser.cdp_url}, ensure_ascii=False))
    if args.keep:
        print("[cdp] --keep: 保持浏览器存活, Ctrl+C 退出")
        try:
            await _wait_enter("按 Enter 关闭浏览器... ")
        except (KeyboardInterrupt, EOFError):
            pass
    await browser.kill()


def main():
    ap = argparse.ArgumentParser(description="browser-use 开锁层: 产出 storage_state / 持久 profile / CDP 端点")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_login = sub.add_parser("login", help="登录并导出 storage_state.json")
    p_login.add_argument("--url", help="登录/入口页 URL")
    p_login.add_argument("--out", default="default.json", help="storage_state 输出路径 (默认保存到 storage_states/)")
    p_login.add_argument("--user-data-dir", help="持久 Chrome profile 目录(sessionStorage 站更稳)")
    p_login.add_argument("--task", help="LLM 自动登录任务(需 ANTHROPIC_API_KEY/OPENAI_API_KEY)")
    p_login.add_argument("--max-steps", type=int, default=25)
    p_login.set_defaults(func=cmd_login)

    p_cdp = sub.add_parser("cdp", help="启动 Chrome 并打印 cdp_url(共享浏览器)")
    p_cdp.add_argument("--url")
    p_cdp.add_argument("--user-data-dir")
    p_cdp.add_argument("--headless", action="store_true")
    p_cdp.add_argument("--keep", action="store_true", help="保持浏览器存活")
    p_cdp.set_defaults(func=cmd_cdp)

    args = ap.parse_args()
    asyncio.run(args.func(args))


if __name__ == "__main__":
    main()
