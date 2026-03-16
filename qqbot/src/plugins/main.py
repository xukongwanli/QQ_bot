import base64

import httpx
from nonebot import get_plugin_config, logger, on_message
from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent,
    Message,
    PrivateMessageEvent,
)
from nonebot.rule import to_me
from openai import AsyncOpenAI
from pydantic import BaseModel


class Config(BaseModel):
    openai_api_key: str
    openai_model: str = "gpt-4o"


plugin_config = get_plugin_config(Config)
logger.info(f"Plugin loaded — using model: {plugin_config.openai_model}")

client = AsyncOpenAI(api_key=plugin_config.openai_api_key)

# 1. 处理私聊消息 (只要是私聊就回复)
private_chat = on_message(
    priority=10,
    block=True,
    rule=lambda event: isinstance(event, PrivateMessageEvent),
)

# 2. 处理群聊消息 (需要 @机器人)
group_chat = on_message(
    priority=10,
    block=True,
    rule=to_me() & (lambda event: isinstance(event, GroupMessageEvent)),
)


async def _download_image_as_data_url(url: str) -> str | None:
    """下载图片并转为 base64 data URL,供 OpenAI API 使用。"""
    try:
        async with httpx.AsyncClient(timeout=30) as http:
            resp = await http.get(url)
            resp.raise_for_status()
            mime = resp.headers.get("content-type", "image/jpeg")
            b64 = base64.b64encode(resp.content).decode()
            return f"data:{mime};base64,{b64}"
    except Exception:  # noqa: BLE001
        logger.exception(f"Failed to download image: {url}")
        return None


def _extract_content(message: Message) -> tuple[str, list[str]]:
    """从消息中提取纯文本和图片 URL 列表。"""
    text = message.extract_plain_text().strip()
    images = [
        seg.data["url"]
        for seg in message
        if seg.type == "image" and "url" in seg.data
    ]
    return text, images


async def get_ai_response(text: str, image_urls: list[str] | None = None) -> str:
    """调用 OpenAI API 获取回复，支持纯文本与图文混合输入。"""
    try:
        if image_urls:
            # 下载图片并转为 base64（QQ CDN URL 外部不可访问）
            data_urls = [
                data_url
                for url in image_urls
                if (data_url := await _download_image_as_data_url(url))
            ]
            if not data_urls and not text:
                return "图片下载失败了，请重新发送试试。"

            content: list[dict] = [
                {"type": "text", "text": text or "看看这张图片，给出你的看法"},
                *[{"type": "image_url", "image_url": {"url": u}} for u in data_urls],
            ]
            user_content: list[dict] | str = content
        else:
            user_content = text

        response = await client.chat.completions.create(
            model=plugin_config.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是2.2生日。字榆朴 名如月 号称三界五行中睡懒觉大王 皇家在逃巧克力猫猫公主"
                        " 曾被称为小月月的 脚踩爱因斯坦 手擒麦克斯韦"
                        " 在世界金融中心上海潜心修炼机械与人体医学的半步天才兼小说散文家"
                    ),
                },
                {"role": "user", "content": user_content},
            ],
            stream=False,
        )
        return response.choices[0].message.content or "(无回复)"
    except Exception as e:  # noqa: BLE001
        logger.exception(f"OpenAI API error: {e!s}")
        return f"猪脑过载了,请稍后再试... (错误: {e!s})"


@private_chat.handle()
async def handle_private(event: PrivateMessageEvent) -> None:
    text, images = _extract_content(event.get_message())
    if not text and not images:
        return

    reply = await get_ai_response(text, images)
    await private_chat.finish(reply)


@group_chat.handle()
async def handle_group(event: GroupMessageEvent) -> None:
    text, images = _extract_content(event.get_message())
    if not text and not images:
        return

    reply = await get_ai_response(text, images)
    await group_chat.finish(reply, at_sender=True)
