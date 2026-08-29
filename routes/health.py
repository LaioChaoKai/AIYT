from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__)

@health_bp.route("/", methods=["GET"])
def index():
    return "YouTube 小說名稱搜尋器 LINE Bot 運作中！", 200

@health_bp.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "online",
        "service": "YouTube Novel Finder LINE Bot",
        "version": "1.0.0"
    }), 200
