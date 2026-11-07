import os

from dotenv import load_dotenv
from flask import Flask
from werkzeug.serving import is_running_from_reloader

from api.api import api_bp
from backstage.views.backstage import backstage_bp
from database.location_replay import location_replay
from frontstage.views.frontstage import frontstage_bp

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key')  # 正式使用時請在 .env 設定 SECRET_KEY

# 註冊 Blueprint：新增功能時請寫在各自的 Blueprint 裡，不需要修改這個檔案
app.register_blueprint(frontstage_bp, url_prefix='/')           # 前台：乘客使用的頁面
app.register_blueprint(backstage_bp, url_prefix='/backstage')   # 後台：管理者 CMS、班表、分析
app.register_blueprint(api_bp, url_prefix='/api')               # API：回傳 JSON 給前端 JavaScript

if __name__ == '__main__':
    with location_replay(app.logger, enabled=is_running_from_reloader()):
        app.run(debug=True, use_reloader=True)
