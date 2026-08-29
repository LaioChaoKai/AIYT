import logging
import traceback
import requests
import urllib.parse
from flask import Blueprint, render_template, request, jsonify
from services.youtube_service import get_youtube_video_info, fetch_oembed_metadata, fetch_page_meta_description, fetch_transcript, extract_video_id, HEADERS
from services.gemini_service import analyze_novel_info

logger = logging.getLogger(__name__)

health_bp = Blueprint("health", __name__)

@health_bp.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@health_bp.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "online",
        "service": "YouTube Novel Finder",
        "version": "1.3.0"
    }), 200

@health_bp.route("/api/search", methods=["POST"])
def api_search():
    data = request.get_json() or {}
    youtube_url = data.get("url", "").strip()

    if not youtube_url:
        return jsonify({"error": "請提供有效的 YouTube 影片網址"}), 400

    try:
        logger.info(f"網頁端收到搜尋請求: {youtube_url}")
        video_data = get_youtube_video_info(youtube_url)

        if "error" in video_data:
            return jsonify({"error": video_data["error"]}), 400

        # 若未抓到標題與字幕，直接回傳抓取到的 raw 結構方便 debug
        if not video_data.get("title") and not video_data.get("transcript") and not video_data.get("description"):
            return jsonify({
                "result": "❌ 無法取得影片的標題、說明欄或字幕內容，無法分析。",
                "debug_video_data": video_data
            }), 200

        result_text = analyze_novel_info(video_data)
        return jsonify({
            "result": result_text,
            "video_data_summary": {
                "title": video_data.get("title"),
                "uploader": video_data.get("uploader"),
                "desc_len": len(video_data.get("description", "")),
                "transcript_len": len(video_data.get("transcript", ""))
            }
        }), 200

    except Exception as e:
        logger.error(f"API 搜尋時發生錯誤: {e}")
        return jsonify({"error": f"伺服器處理失敗：{str(e)}"}), 500

@health_bp.route("/api/debug_key", methods=["GET"])
def debug_key():
    import os
    key = os.getenv("GEMINI_API_KEY", "")
    return jsonify({
        "key_exists": bool(key),
        "key_length": len(key),
        "key_prefix": key[:8] if key else "",
        "key_suffix": key[-5:] if key else ""
    })

