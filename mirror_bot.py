#!/usr/bin/env python3
"""
Telegram镜像Bot - 完全工作版
支持消息编辑翻页机制
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional
from datetime import datetime

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.raw.functions.messages import GetBotCallbackAnswer

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters as tg_filters
)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# ================== 配置 ==================
API_ID = 24660516
API_HASH = "eae564578880a59c9963916ff1bbbd3a"
SESSION_NAME = "my_session"
BOT_TOKEN = "8480726943:AAHh4jXSjYDPox_Vd0kG2jwx1MQVdwsS6Qw"
TARGET_BOT = "@openaiw_bot"

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# ================== 全局状态 ==================
class GlobalState:
    def __init__(self):
        self.pyrogram_client: Optional[Client] = None
        self.target_bot_id: Optional[int] = None
        self.bot_app: Optional[Application] = None

        # 核心映射关系
        self.pyrogram_to_telegram = {}  # pyrogram_msg_id -> telegram_msg_id
        self.telegram_to_pyrogram = {}  # telegram_msg_id -> pyrogram_msg_id
        self.callback_data_map = {}     # telegram_callback_id -> (pyrogram_msg_id, original_callback_data)

state = GlobalState()

# ================== Pyrogram客户端初始化 ==================
async def setup_pyrogram():
    """初始化Pyrogram客户端"""
    try:
        state.pyrogram_client = Client(
            SESSION_NAME,
            api_id=API_ID,
            api_hash=API_HASH
        )

        await state.pyrogram_client.start()
        logger.info("✅ Pyrogram客户端已启动")

        target = await state.pyrogram_client.get_users(TARGET_BOT)
        state.target_bot_id = target.id
        logger.info(f"✅ 目标Bot: {target.username} (ID: {target.id})")

        # 监听消息编辑（翻页时Bot会编辑原消息）
        @state.pyrogram_client.on_edited_message(filters.user(state.target_bot_id))
        async def on_message_edited(_, message: Message):
            """当Bot编辑消息时（翻页）"""
            logger.info(f"检测到消息编辑: #{message.id}")

            # 查找对应的Telegram消息
            if message.id in state.pyrogram_to_telegram:
                telegram_msg_id = state.pyrogram_to_telegram[message.id]
                logger.info(f"更新Telegram消息: #{telegram_msg_id}")

                # 通过Bot更新对应的消息
                await update_telegram_message(telegram_msg_id, message)

        logger.info("✅ 消息监听器已设置")
        return True

    except Exception as e:
        logger.error(f"Pyrogram初始化失败: {e}")
        return False

# ================== 更新Telegram消息 ==================
async def update_telegram_message(telegram_msg_id: int, pyrogram_msg: Message):
    """更新用户看到的Telegram消息"""
    try:
        # 提取新的内容和键盘
        text_content = ""
        reply_markup = None

        # 获取HTML格式
        try:
            if pyrogram_msg.text:
                text_content = pyrogram_msg.text.html
        except:
            text_content = pyrogram_msg.text or ""

        # 处理inline keyboard
        if pyrogram_msg.reply_markup and pyrogram_msg.reply_markup.inline_keyboard:
            buttons = []
            for row in pyrogram_msg.reply_markup.inline_keyboard:
                button_row = []
                for btn in row:
                    if btn.url:
                        button_row.append(InlineKeyboardButton(
                            text=btn.text,
                            url=btn.url
                        ))
                    elif btn.callback_data:
                        # 创建新的callback ID
                        callback_id = f"cb_{telegram_msg_id}_{len(state.callback_data_map)}"
                        state.callback_data_map[callback_id] = (
                            pyrogram_msg.id,
                            btn.callback_data
                        )

                        button_row.append(InlineKeyboardButton(
                            text=btn.text,
                            callback_data=callback_id[:64]
                        ))

                if button_row:
                    buttons.append(button_row)

            if buttons:
                reply_markup = InlineKeyboardMarkup(buttons)

        # 通过Bot API编辑消息
        if state.bot_app and state.bot_app.bot:
            await state.bot_app.bot.edit_message_text(
                text=text_content,
                chat_id=telegram_msg_id // 1000000000,  # 简化的chat_id提取
                message_id=telegram_msg_id % 1000000000,  # 简化的message_id提取
                parse_mode='HTML',
                reply_markup=reply_markup
            )

            logger.info(f"✅ 消息已更新")

    except Exception as e:
        logger.error(f"更新消息失败: {e}")

# ================== 发送命令并获取响应 ==================
async def send_and_get_response(command: str) -> Optional[Message]:
    """发送命令并获取第一个响应"""
    try:
        logger.info(f"发送命令: {command}")

        # 发送命令
        await state.pyrogram_client.send_message(
            state.target_bot_id,
            command
        )

        # 等待响应
        await asyncio.sleep(2)

        # 获取最新消息
        async for msg in state.pyrogram_client.get_chat_history(state.target_bot_id, limit=5):
            if msg.from_user and msg.from_user.id == state.target_bot_id:
                # 检查是否是新消息（5秒内）
                if time.time() - msg.date.timestamp() < 5:
                    logger.info(f"收到响应: #{msg.id}")
                    return msg

        logger.warning("没有收到响应")
        return None

    except Exception as e:
        logger.error(f"发送命令失败: {e}")
        return None

# ================== 转发消息到用户 ==================
async def forward_to_user(update: Update, pyrogram_msg: Message) -> Optional[int]:
    """转发消息到用户，返回Telegram消息ID"""
    try:
        # 处理HTML格式
        text_content = ""
        try:
            if pyrogram_msg.text:
                text_content = pyrogram_msg.text.html
            elif pyrogram_msg.caption:
                text_content = pyrogram_msg.caption.html
        except:
            text_content = pyrogram_msg.text or pyrogram_msg.caption or ""

        # 处理inline keyboard
        reply_markup = None
        if pyrogram_msg.reply_markup and pyrogram_msg.reply_markup.inline_keyboard:
            buttons = []
            for row in pyrogram_msg.reply_markup.inline_keyboard:
                button_row = []
                for btn in row:
                    if btn.url:
                        button_row.append(InlineKeyboardButton(
                            text=btn.text,
                            url=btn.url
                        ))
                    elif btn.callback_data:
                        # 创建唯一的callback ID
                        callback_id = f"cb_{time.time():.0f}_{len(state.callback_data_map)}"

                        # 存储映射关系
                        state.callback_data_map[callback_id] = (
                            pyrogram_msg.id,
                            btn.callback_data
                        )

                        button_row.append(InlineKeyboardButton(
                            text=btn.text,
                            callback_data=callback_id[:64]
                        ))

                if button_row:
                    buttons.append(button_row)

            if buttons:
                reply_markup = InlineKeyboardMarkup(buttons)

        # 发送消息
        sent = None
        if pyrogram_msg.photo:
            sent = await update.message.reply_photo(
                photo=pyrogram_msg.photo.file_id,
                caption=text_content[:1024],
                parse_mode='HTML',
                reply_markup=reply_markup
            )
        elif text_content:
            sent = await update.message.reply_text(
                text_content[:4000],
                parse_mode='HTML',
                reply_markup=reply_markup,
                disable_web_page_preview=False
            )

        if sent:
            # 存储消息ID映射
            state.pyrogram_to_telegram[pyrogram_msg.id] = sent.message_id
            state.telegram_to_pyrogram[sent.message_id] = pyrogram_msg.id
            logger.info(f"✅ 转发成功: Pyrogram#{pyrogram_msg.id} -> Telegram#{sent.message_id}")
            return sent.message_id

    except Exception as e:
        logger.error(f"转发失败: {e}")
        return None

# ================== Bot命令处理器 ==================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /start 命令"""
    logger.info(f"用户 {update.effective_user.id} 执行 /start")
    # 静默处理，不发送欢迎消息

async def proxy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """代理命令到目标Bot"""
    command = update.message.text
    user_id = update.effective_user.id

    logger.info(f"用户 {user_id} 执行: {command}")

    processing = await update.message.reply_text("⏳ 处理中...")

    try:
        # 发送命令并获取响应
        response = await send_and_get_response(command)

        if not response:
            await processing.edit_text("⏱ 暂时无响应，请稍后重试")
            return

        # 删除处理提示
        await processing.delete()

        # 转发响应
        await forward_to_user(update, response)

    except Exception as e:
        logger.error(f"命令处理失败: {e}")
        await processing.edit_text("❌ 处理失败")

# ================== Callback处理（翻页） ==================
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理翻页等callback"""
    query = update.callback_query
    callback_id = query.data

    await query.answer("正在加载...")

    logger.info(f"处理callback: {callback_id}")

    # 获取映射信息
    if callback_id not in state.callback_data_map:
        await query.answer("按钮已过期", show_alert=True)
        return

    pyrogram_msg_id, original_callback = state.callback_data_map[callback_id]

    try:
        # 准备callback数据
        if not isinstance(original_callback, bytes):
            original_callback = original_callback.encode() if original_callback else b''

        logger.info(f"调用GetBotCallbackAnswer: msg_id={pyrogram_msg_id}")

        # 调用原始callback
        result = await state.pyrogram_client.invoke(
            GetBotCallbackAnswer(
                peer=await state.pyrogram_client.resolve_peer(state.target_bot_id),
                msg_id=pyrogram_msg_id,
                data=original_callback
            )
        )

        logger.info("✅ Callback调用成功")

        # Bot会编辑原消息，等待编辑事件
        await asyncio.sleep(1)

        # 手动检查并更新（作为备份）
        async for msg in state.pyrogram_client.get_chat_history(state.target_bot_id, limit=5):
            if msg.id == pyrogram_msg_id:
                # 获取更新后的内容
                try:
                    html_text = msg.text.html if msg.text else ""
                except:
                    html_text = msg.text or ""

                # 处理新的键盘
                reply_markup = None
                if msg.reply_markup and msg.reply_markup.inline_keyboard:
                    buttons = []
                    for row in msg.reply_markup.inline_keyboard:
                        button_row = []
                        for btn in row:
                            if btn.url:
                                button_row.append(InlineKeyboardButton(
                                    text=btn.text,
                                    url=btn.url
                                ))
                            elif btn.callback_data:
                                # 创建新的callback映射
                                new_callback_id = f"cb_{time.time():.0f}_{len(state.callback_data_map)}"
                                state.callback_data_map[new_callback_id] = (
                                    pyrogram_msg_id,
                                    btn.callback_data
                                )

                                button_row.append(InlineKeyboardButton(
                                    text=btn.text,
                                    callback_data=new_callback_id[:64]
                                ))

                        if button_row:
                            buttons.append(button_row)

                    if buttons:
                        reply_markup = InlineKeyboardMarkup(buttons)

                # 编辑用户的消息
                await query.edit_message_text(
                    html_text[:4000],
                    parse_mode='HTML',
                    reply_markup=reply_markup
                )

                logger.info("✅ 页面已更新")
                break

    except Exception as e:
        logger.error(f"Callback处理失败: {e}")
        await query.answer("操作失败", show_alert=True)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理普通文本消息"""
    text = update.message.text
    await proxy_command(update, context)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """显示状态"""
    status = f"""📊 系统状态

✅ 镜像Bot工作正常
🎯 目标: {TARGET_BOT}
📝 消息映射: {len(state.pyrogram_to_telegram)}
🔗 Callback映射: {len(state.callback_data_map)}

时间: {datetime.now().strftime('%H:%M:%S')}"""

    await update.message.reply_text(status)

# ================== 主程序 ==================
async def main():
    """主函数"""
    logger.info("="*50)
    logger.info("Telegram镜像Bot - 完全工作版")
    logger.info("支持消息编辑翻页")
    logger.info("="*50)

    # 初始化Pyrogram
    if not await setup_pyrogram():
        logger.error("初始化失败")
        return

    # 创建Bot应用
    state.bot_app = Application.builder().token(BOT_TOKEN).build()

    # 注册处理器
    state.bot_app.add_handler(CommandHandler("start", start_command))
    state.bot_app.add_handler(CommandHandler("status", status_command))
    state.bot_app.add_handler(CommandHandler("search", proxy_command))
    state.bot_app.add_handler(CommandHandler("topchat", proxy_command))
    state.bot_app.add_handler(CommandHandler("text", proxy_command))
    state.bot_app.add_handler(CommandHandler("human", proxy_command))

    # Callback处理器（翻页）
    state.bot_app.add_handler(CallbackQueryHandler(handle_callback))

    # 普通文本
    state.bot_app.add_handler(MessageHandler(
        tg_filters.TEXT & ~tg_filters.COMMAND,
        handle_text
    ))

    logger.info("✅ 处理器已注册")

    # 启动Bot
    await state.bot_app.initialize()
    await state.bot_app.start()
    await state.bot_app.updater.start_polling(drop_pending_updates=True)

    logger.info("="*50)
    logger.info("✅ 系统已启动")
    logger.info(f"Bot: @zhongjiesanjie_bot")
    logger.info(f"镜像: {TARGET_BOT}")
    logger.info("✅ 翻页功能已支持")
    logger.info("="*50)

    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("\n正在关闭...")
    finally:
        await state.bot_app.updater.stop()
        await state.bot_app.stop()
        await state.bot_app.shutdown()
        if state.pyrogram_client:
            await state.pyrogram_client.stop()
        logger.info("✅ 已安全关闭")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"错误: {e}")