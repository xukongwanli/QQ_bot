from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, PrivateMessageEvent, GroupMessageEvent, Message
from nonebot.rule import to_me
from nonebot.params import CommandArg
from openai import AsyncOpenAI
import os
from dotenv import load_dotenv


# 加载环境变量

load_dotenv()
API_KEY = os.getenv("DEEPSEEK_API_KEY")
MODEL_NAME = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# 初始化 OpenAI 客户端 (DeepSeek 兼容)
client = AsyncOpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")

# 1. 处理私聊消息 (只要是私聊就回复)
# rule=None 表示所有私聊都触发，你也可以加条件
private_chat = on_message(priority=10, block=True, rule=lambda event: isinstance(event, PrivateMessageEvent))

# 2. 处理群聊消息 (需要 @机器人)
# rule=to_me() 确保只有被 @ 时才触发
group_chat = on_message(priority=10, block=True, rule=to_me() & (lambda event: isinstance(event, GroupMessageEvent)))

async def get_deepseek_response(text: str) -> str:
    """调用 DeepSeek API 获取回复"""
    try:
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "你是2.2生日。字榆朴 名如月 号称三界五行中睡懒觉大王 皇家在逃巧克力猫猫公主 曾被称为小月月的 脚踩爱因斯坦 手擒麦克斯韦 在世界金融中心上海潜心修炼机械与人体医学的半步天才兼小说散文家"},
                {"role": "user", "content": text},
            ],
            stream=False
        )
        result=response.choices[0].message.content
        print(f"[DeepSeek 回复] {result[:100]}")  # 加这行
        return result
    except Exception as e:
        return f"猪脑过载了,请稍后再试... (错误: {str(e)})"

@private_chat.handle()
async def handle_private(event: PrivateMessageEvent):
    user_msg = event.get_plaintext().strip()
    if not user_msg:
        return
    
    # 发送“正在输入”提示（可选）
    # await private_chat.send("思考中...") 
    
    reply = await get_deepseek_response(user_msg)
    await private_chat.finish(reply)

@group_chat.handle()
async def handle_group(bot: Bot, event: GroupMessageEvent):
    # 获取纯文本内容（会自动去除 @ 部分）
    user_msg = event.get_plaintext().strip()
    
    if not user_msg:
        return

    reply = await get_deepseek_response(user_msg)
    # finish 会自动回复，在群里通常是直接发消息，如果需要 @回去，可以使用 MessageSegment
    await group_chat.finish(reply, at_sender=True) 
