# -*- coding: utf-8 -*-
"""
see_screen.py — 给纯文本模型的"眼睛"。
截屏（或读取指定图片）→ 发给豆包 Doubao Seed 2.1 Pro（火山方舟，支持视觉）→ 输出文字描述。
主模型（Claude Code 里的 GLM 文本模型）只需要读本脚本的 stdout，永远不接触图片本身。

用法:
  python tools/see_screen.py                          # 截全屏并描述
  python tools/see_screen.py -q "登录二维码出现了吗"    # 截全屏并回答特定问题
  python tools/see_screen.py -i path/to/img.png       # 解析已有图片
  python tools/see_screen.py --keep                   # 保留截图文件（默认用完即删）

依赖: 全局 python (3.12) + pillow + requests（均已安装）
环境变量: ARK_API_KEY（火山方舟 API Key）
"""
import argparse
import base64
import io
import os
import sys
import tempfile

MODEL = os.environ.get("ARK_VISION_MODEL", "doubao-seed-2-1-pro-260628")
ARK_URL = "https://ark.cn-beijing.volces.com/api/v3/responses"

DEFAULT_PROMPT = (
    "这是一张 Windows 桌面截图。请用中文简洁描述：当前前台窗口是什么、"
    "页面主要内容、有无弹窗/二维码/验证码/错误提示，以及任何值得注意的状态。"
)


def grab_screenshot() -> bytes:
    from PIL import ImageGrab

    img = ImageGrab.grab(all_screens=False)
    # 缩到长边 <=1600，省 token 且足够识别 UI
    if max(img.size) > 1600:
        ratio = 1600 / max(img.size)
        img = img.resize((int(img.width * ratio), int(img.height * ratio)))
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-q", "--question", default=None, help="针对画面提的问题")
    ap.add_argument("-i", "--image", default=None, help="解析指定图片而不是现场截屏")
    ap.add_argument("--keep", action="store_true", help="保留截图文件并打印路径")
    args = ap.parse_args()

    api_key = os.environ.get("ARK_API_KEY")
    if not api_key:
        print("[ERROR] 未设置环境变量 ARK_API_KEY（火山方舟 API Key）。", file=sys.stderr)
        print("获取方式: https://console.volcengine.com/ark → API Key 管理", file=sys.stderr)
        return 2

    image_url = None
    if args.image and args.image.startswith(("http://", "https://")):
        # 远程图片直接传 URL，方舟服务端自己拉取，不用本地下载编码
        image_url = args.image
    elif args.image:
        with open(args.image, "rb") as f:
            img_bytes = f.read()
        ext = os.path.splitext(args.image)[1].lstrip(".").lower() or "png"
        mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
        image_url = f"data:{mime};base64,{base64.b64encode(img_bytes).decode()}"
    else:
        img_bytes = grab_screenshot()
        mime = "image/jpeg"
        if args.keep:
            path = os.path.join(tempfile.gettempdir(), "see_screen_last.jpg")
            with open(path, "wb") as f:
                f.write(img_bytes)
            print(f"[screenshot saved] {path}")
        image_url = f"data:{mime};base64,{base64.b64encode(img_bytes).decode()}"

    prompt = args.question or DEFAULT_PROMPT

    import requests

    resp = requests.post(
        ARK_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": MODEL,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_image", "image_url": image_url},
                        {"type": "input_text", "text": prompt},
                    ],
                }
            ],
            # 视觉描述不需要深度思考，关掉省时间省钱
            "thinking": {"type": "disabled"},
        },
        timeout=120,
    )
    if resp.status_code != 200:
        print(f"[ERROR] Ark API {resp.status_code}: {resp.text[:500]}", file=sys.stderr)
        return 1

    data = resp.json()
    # Responses API 结构: output 是一个列表，其中 type=="message" 的项里含 content -> output_text
    text_out = []
    for item in data.get("output", []):
        if item.get("type") == "message":
            for c in item.get("content", []):
                if c.get("type") == "output_text":
                    text_out.append(c.get("text", ""))
    if not text_out:
        print(f"[ERROR] 未解析到输出，原始响应: {str(data)[:800]}", file=sys.stderr)
        return 1
    print("\n".join(text_out).strip())
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(main())
