import os
import secrets

from dotenv import load_dotenv
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.serving import is_running_from_reloader

from api.api import api_bp
from backstage.views.backstage import backstage_bp
from database.location_replay import location_replay
from frontstage.views.frontstage import frontstage_bp

load_dotenv()

# 開發時在 .env 加 FLASK_DEBUG=1；對外開放（ngrok）時不要設定，避免除錯器暴露在網路上
DEBUG = os.getenv('FLASK_DEBUG') == '1'

app = Flask(__name__)
# 請在 .env 設定 SECRET_KEY；未設定時改用隨機值（重啟後需重新登入，但不會被偽造登入狀態）
app.secret_key = os.getenv('SECRET_KEY') or secrets.token_hex(32)
# 讓 Flask 正確辨識 ngrok 等反向代理轉送的 https 與網域（本機直接連線時不影響）
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# 註冊 Blueprint：新增功能時請寫在各自的 Blueprint 裡，不需要修改這個檔案
app.register_blueprint(frontstage_bp, url_prefix='/')           # 前台：乘客使用的頁面
app.register_blueprint(backstage_bp, url_prefix='/backstage')   # 後台：管理者 CMS、班表、分析
app.register_blueprint(api_bp, url_prefix='/api')               # API：回傳 JSON 給前端 JavaScript

if __name__ == '__main__':
    # debug 模式的 reloader 會開兩個行程，只在子行程啟動即時位置模擬，避免重複寫入
    replay_enabled = (not DEBUG) or is_running_from_reloader()
    with location_replay(app.logger, enabled=replay_enabled):
        app.run(debug=DEBUG, use_reloader=DEBUG)
