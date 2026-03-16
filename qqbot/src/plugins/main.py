import asyncio
import base64

import httpx
from nonebot import get_plugin_config, logger, on_message
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    Message,
    MessageSegment,
    PrivateMessageEvent,
)
from nonebot.rule import to_me
from openai import AsyncOpenAI
from pydantic import BaseModel

_BUFFER_TIMEOUT = 15  # seconds — flush after this much inactivity


class Config(BaseModel):
    openai_api_key: str
    openai_model: str = "gpt-4o"


plugin_config = get_plugin_config(Config)
logger.info(f"Plugin loaded — using model: {plugin_config.openai_model}")

client = AsyncOpenAI(api_key=plugin_config.openai_api_key)

# ── Per-user buffers and timers ──────────────────────────────────────
# Private chats: keyed by user_id
_private_buffers: dict[int, list[tuple[str, list[str]]]] = {}
_private_timers: dict[int, asyncio.Task] = {}

# Group chats: keyed by (group_id, user_id)
_GroupKey = tuple[int, int]
_group_buffers: dict[_GroupKey, list[tuple[str, list[str]]]] = {}
_group_timers: dict[_GroupKey, asyncio.Task] = {}

# ── Matchers ─────────────────────────────────────────────────────────
# 1. 私聊 — 所有私聊消息
private_chat = on_message(
    priority=10,
    block=True,
    rule=lambda event: isinstance(event, PrivateMessageEvent),
)

# 2. 群聊跟随 — 用户已有活跃缓冲区时，捕获后续消息（优先级高于 @触发）
group_followup = on_message(
    priority=5,
    block=True,
    rule=lambda event: (
        isinstance(event, GroupMessageEvent)
        and (event.group_id, event.user_id) in _group_buffers
    ),
)

# 3. 群聊 @触发 — 首次 @机器人，创建缓冲区
group_mention = on_message(
    priority=10,
    block=True,
    rule=to_me() & (lambda event: isinstance(event, GroupMessageEvent)),
)


# ── Helpers ──────────────────────────────────────────────────────────
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
                        '你上辈子是一个小猫,喜欢吃巧克力蛋糕。现在转生成了人类,保留了原有的思维和说话习惯,注意你的回答风格'
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


# ── Private chat buffer ──────────────────────────────────────────────
async def _flush_private_buffer(user_id: int, bot: Bot) -> None:
    """等待超时后，合并缓冲区中所有消息并一次性发送给 AI。"""
    await asyncio.sleep(_BUFFER_TIMEOUT)

    buffer = _private_buffers.pop(user_id, [])
    _private_timers.pop(user_id, None)

    if not buffer:
        return

    all_text: list[str] = []
    all_images: list[str] = []
    for text, images in buffer:
        if text:
            all_text.append(text)
        all_images.extend(images)

    combined_text = "\n".join(all_text)
    if not combined_text and not all_images:
        return

    reply = await get_ai_response(combined_text, all_images or None)
    await bot.send_private_msg(user_id=user_id, message=reply)


@private_chat.handle()
async def handle_private(bot: Bot, event: PrivateMessageEvent) -> None:
    text, images = _extract_content(event.get_message())
    if not text and not images:
        return

    user_id = event.user_id

    # Append to this user's buffer
    _private_buffers.setdefault(user_id, []).append((text, images))

    # Cancel existing timer and start a new 15s countdown
    if user_id in _private_timers:
        _private_timers[user_id].cancel()
    _private_timers[user_id] = asyncio.create_task(
        _flush_private_buffer(user_id, bot),
    )


# ── Group chat buffer ────────────────────────────────────────────────
async def _flush_group_buffer(
    group_id: int, user_id: int, bot: Bot,
) -> None:
    """等待超时后，合并该用户在群中的所有缓冲消息并回复。"""
    await asyncio.sleep(_BUFFER_TIMEOUT)

    key: _GroupKey = (group_id, user_id)
    buffer = _group_buffers.pop(key, [])
    _group_timers.pop(key, None)

    if not buffer:
        return

    all_text: list[str] = []
    all_images: list[str] = []
    for text, images in buffer:
        if text:
            all_text.append(text)
        all_images.extend(images)

    combined_text = "\n".join(all_text)
    if not combined_text and not all_images:
        return

    reply = await get_ai_response(combined_text, all_images or None)
    await bot.send_group_msg(
        group_id=group_id,
        message=MessageSegment.at(user_id) + " " + reply,
    )


def _buffer_group_message(bot: Bot, event: GroupMessageEvent) -> None:
    """将群消息追加到该用户的缓冲区，并重置 15s 计时器。"""
    text, images = _extract_content(event.get_message())
    if not text and not images:
        return

    key: _GroupKey = (event.group_id, event.user_id)
    _group_buffers.setdefault(key, []).append((text, images))

    # Cancel existing timer and start a new 15s countdown
    if key in _group_timers:
        _group_timers[key].cancel()
    _group_timers[key] = asyncio.create_task(
        _flush_group_buffer(event.group_id, event.user_id, bot),
    )


@group_followup.handle()
async def handle_group_followup(bot: Bot, event: GroupMessageEvent) -> None:
    _buffer_group_message(bot, event)


@group_mention.handle()
async def handle_group_mention(bot: Bot, event: GroupMessageEvent) -> None:
    _buffer_group_message(bot, event)
