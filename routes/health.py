import logging
from flask import Blueprint, render_template, request, jsonify
from services.youtube_service import get_youtube_video_info
from services.gemini_service import analyze_novel_info

logger = logging.getLogger(__name__)

health_bp = Blueprint("health", __name__)

@health_bp.route("/", methods=["GET"])
def index():
    """渲染前端網頁版介面 (無需使用者輸入 Key，直接貼 URL 即可查)"""
    return render_template("index.html")

@health_bp.route("/health", methods=["GET"])
def health_check():
    """伺服器健康檢查 API"""
    return jsonify({
        "status": "online",
        "service": "YouTube Novel Finder",
        "version": "1.2.0"
    }), 200

@health_bp.route("/api/search", methods=["POST"])
def api_search():
    """前端網頁 AJAX 搜尋 API 入口"""
    data = request.get_json() or {}
    youtube_url = data.get("url", "").strip()

    if not youtube_url:
        return jsonify({"error": "請提供有效的 YouTube 影片網址"}), 400

    try:
        logger.info(f"網頁端收到搜尋請求: {youtube_url}")
        video_data = get_youtube_video_info(youtube_url)

        if "error" in video_data:
            return jsonify({"error": video_data["error"]}), 400

        result_text = analyze_novel_info(video_data)
        return jsonify({"result": result_text}), 200

    except Exception as e:
        logger.error(f"API 搜尋時發生錯誤: {e}")
        return jsonify({"error": f"伺服器處理失敗：{str(e)}"}), 500
