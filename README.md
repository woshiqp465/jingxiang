# 脚本转发 (Telegram Mirror Bot)

一个功能强大的 Telegram 机器人镜像系统，可以完美镜像其他 Bot 的功能，支持消息转发、格式保留和翻页功能。

## 功能特性

- ✅ 完美镜像 @openaiw_bot 的搜索功能
- ✅ 保留原始消息格式（HTML、链接、表情符号）
- ✅ 支持翻页功能（通过消息编辑实现）
- ✅ 支持多种命令：`/search`、`/topchat`、`/text`、`/human`
- ✅ 静默启动，无干扰提示
- ✅ 二进制 callback 数据处理

## 安装步骤

### 1. 克隆仓库

```bash
git clone https://github.com/[your-username]/telegram-mirror-bot.git
cd telegram-mirror-bot
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置

#### 获取 API 凭证

1. 访问 https://my.telegram.org
2. 登录你的 Telegram 账号
3. 创建一个应用，获取 `API_ID` 和 `API_HASH`

#### 创建 Bot

1. 在 Telegram 中找 @BotFather
2. 创建新 Bot：`/newbot`
3. 保存 Bot Token

#### 生成 Session

```python
from pyrogram import Client

api_id = YOUR_API_ID
api_hash = "YOUR_API_HASH"

app = Client("my_session", api_id=api_id, api_hash=api_hash)
app.run()
```

运行后输入手机号和验证码，会生成 `my_session.session` 文件。

### 4. 修改配置

编辑 `mirror_bot.py`，修改以下配置：

```python
API_ID = YOUR_API_ID
API_HASH = "YOUR_API_HASH"
BOT_TOKEN = "YOUR_BOT_TOKEN"
TARGET_BOT = "@openaiw_bot"  # 或其他要镜像的 Bot
```

## 使用方法

### 启动机器人

```bash
python mirror_bot.py
```

### 使用命令

在 Telegram 中与你的 Bot 对话：

- `/search <关键词>` - 搜索频道和群组
- `/topchat` - 查看热门聊天
- `/text <文本>` - 搜索包含特定文本的消息
- `/human <姓名>` - 搜索用户
- `/status` - 查看系统状态

### 翻页功能

当搜索结果超过 20 条时，会显示翻页按钮：
- 点击 `➡️ 2` 查看第二页
- 点击 `⬅️` 返回上一页

## 技术特点

### 消息编辑翻页

本项目的核心创新是发现了 @openaiw_bot 使用消息编辑来实现翻页，而不是发送新消息。通过监听 `on_edited_message` 事件，完美实现了翻页功能。

### 双客户端架构

- **Pyrogram 客户端**：使用用户账号监听目标 Bot
- **python-telegram-bot**：处理用户交互

### 消息映射

维护 Pyrogram 消息 ID 和 Telegram 消息 ID 的映射关系，确保消息更新的准确性。

## 项目结构

```
telegram-mirror-bot/
├── mirror_bot.py      # 主程序
├── requirements.txt   # 依赖列表
├── README.md         # 说明文档
└── my_session.session # Session 文件（运行后生成）
```

## 注意事项

1. **安全性**：妥善保管 `session` 文件和 API 凭证
2. **合规性**：遵守 Telegram 服务条款
3. **性能**：建议安装 `tgcrypto` 以提升性能
4. **限制**：遵守 API 调用频率限制

## 常见问题

### Q: 为什么翻页没有反应？

A: 确保正确处理了二进制 callback 数据，本项目已完美解决此问题。

### Q: 如何镜像其他 Bot？

A: 修改 `TARGET_BOT` 变量为目标 Bot 的用户名即可。

### Q: Session 过期怎么办？

A: 删除 `.session` 文件，重新生成即可。

## License

MIT

## 作者

Lucas

## 更新日志

- 2024-09-25：初始版本，支持完整的消息转发和翻页功能