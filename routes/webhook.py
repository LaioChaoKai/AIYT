import os
import re
import threading
import logging
from flask import Blueprint, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi, ReplyMessageRequest, PushMessageRequest, TextMessage
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent, FollowEvent

from services.youtube_service import get_youtube_video_info
from services.gemini_service import analyze_novel_info

logger = logging.getLogger(__name__)

# 建立 Flask Blueprint
line_bp = Blueprint("webhook", __name__)

# LINE Messaging API 配置
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

WELCOME_MESSAGE = (
    "👋 歡迎加入「YouTube 小說名稱 AI 搜尋器」！\n\n"
    "📖 使用教學與說明：\n"
    "1️⃣ 請直接在此對話框中貼上任何 YouTube 小說或動漫解說影片網址（例如 https://youtu.be/...）。\n"
    "2️⃣ AI 將會自動解析影片標題、說明欄與字幕，幫您精準找出原始小說名稱、作者與主角資訊！\n\n"
    "🌐 您也可以隨時使用我們的免登入網頁版：\n"
    "https://ckai.ischaokai.online/"
)

def process_youtube_url_async(user_id: str, youtube_url: str):
    """背景非同步處理 YouTube 解析，避免 LINE Webhook 回應超時"""
    try:
        logger.info(f"開始為用戶 {user_id} 解析 YouTube 網址: {youtube_url}")
        
        # 1. 抓取 YouTube 影片數據 (標題、說明欄、字幕)
        video_data = get_youtube_video_info(youtube_url)
        
        if "error" in video_data:
            result_text = f"❌ 解析失敗：{video_data['error']}"
        else:
            # 2. 丟給 Gemini API 做 AI 分析
            result_text = analyze_novel_info(video_data)
            
        # 3. 使用 Push Message 主動傳送分析結果給使用者
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.push_message(
                PushMessageRequest(
                    to=user_id,
                    messages=[TextMessage(text=result_text)]
                )
            )
        logger.info(f"已成功傳送解析結果給用戶 {user_id}")
        
    except Exception as e:
        logger.error(f"非同步處理過程中發生錯誤: {e}")
        try:
            with ApiClient(configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                line_bot_api.push_message(
                    PushMessageRequest(
                        to=user_id,
                        messages=[TextMessage(text=f"⚠️ 處理影片時發生錯誤：{str(e)}")]
                    )
                )
        except Exception as push_err:
            logger.error(f"無法推送錯誤訊息給用戶: {push_err}")

@line_bp.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        logger.error("無效的 LINE 簽名 (Invalid Signature)")
        abort(400)

    return "OK", 200

@handler.add(FollowEvent)
def handle_follow(event):
    """當使用者加好友或解除封鎖時，自動傳送歡迎與使用說明訊息"""
    logger.info(f"新使用者加好友: {event.source.user_id}")
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=WELCOME_MESSAGE)]
            )
        )

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_message = event.message.text.strip()
    user_id = event.source.user_id

    # 判斷訊息是否包含 YouTube 或 youtu.be 網址
    if "youtube.com" in user_message or "youtu.be" in user_message:
        # 正則提取網址
        url_match = re.search(r'(https?://[^\s]+)', user_message)
        youtube_url = url_match.group(1) if url_match else user_message
        
        # 立即回覆提示訊息（使用 reply_token，避免 LINE 超時）
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="🔍 收到 YouTube 網址！正在分析標題、說明欄與字幕，請稍候...")]
                )
            )
            
        # 開開啟 Thread 在背景非同步執行分析並 Push 訊息
        thread = threading.Thread(
            target=process_youtube_url_async,
            args=(user_id, youtube_url)
        )
        thread.start()
    else:
        # 一般文字訊息回覆引導說明
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=WELCOME_MESSAGE)]
                )
            )
