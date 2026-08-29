import os
import logging
from flask import Flask
from dotenv import load_dotenv

# 載入 .env 環境變數
load_dotenv()

# 設定日誌格式
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

def create_app() -> Flask:
    """使用 Flask Blueprint 架構建立與配置 Flask 應用程式"""
    app = Flask(__name__)

    # 註冊 Blueprints 路由模組
    from routes.health import health_bp
    from routes.webhook import line_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(line_bp)

    logger.info("已成功載入並註冊所有 Flask Blueprints！")
    return app

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
