#!/usr/bin/env python3
"""
创建Pyrogram session文件
"""

from pyrogram import Client

# 配置
API_ID = 24660516
API_HASH = "eae564578880a59c9963916ff1bbbd3a"
SESSION_NAME = "my_session"

print("="*60)
print("Session文件生成器")
print("="*60)
print("请输入手机号（格式：+86xxx）和验证码")
print("="*60)

# 创建客户端
app = Client(
    SESSION_NAME,
    api_id=API_ID,
    api_hash=API_HASH
)

# 运行（会提示输入手机号和验证码）
app.run()

print("\n✅ Session文件创建成功！")
print("文件名: my_session.session")