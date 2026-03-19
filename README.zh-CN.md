# QQ Bot 666

**语言: [English](README.md) | 中文**

一个基于 **NoneBot2** + **OneBot V11** 适配器的 AI QQ 聊天机器人，使用 **OpenAI 兼容 API**（如 DeepSeek）生成回复，通过 **Docker NapCat** 框架连接 QQ 账号。

## 功能特性

- 响应所有私聊消息
- 响应群聊中的 @提及，支持后续消息缓冲
- 15 秒防抖：将连续快速发送的消息合并为一次 AI 请求
- 图片识别支持（下载 QQ CDN 图片并转为 base64 发送）

## 技术栈

- **NoneBot2** — 异步机器人框架
- **OneBot V11** — QQ 协议适配器
- **NapCat (Docker)** — QQ 连接的 OneBot 实现
- **OpenAI SDK** — LLM API 客户端（兼容 DeepSeek、GPT 等）

## 快速开始

1. 启动 NapCat Docker 容器并登录你的 QQ 账号。

2. 在 `qqbot/.env` 中配置环境变量：
   ```
   OPENAI_API_KEY=your-api-key
   OPENAI_MODEL=gpt-4o
   ONEBOT_WS_URLS=["ws://127.0.0.1:3001"]
   ```

3. 安装依赖并运行：
   ```bash
   cd qqbot
   pip install .
   nb run --reload
   ```

## 项目结构

```
qqbot/
├── pyproject.toml              # 依赖与工具配置
├── .env / .env.dev             # 环境变量
└── src/plugins/
    └── main.py                 # 消息处理器与 AI 逻辑
```

## 许可证

MIT
