from flask import Blueprint, render_template

# 前台 Blueprint，網址前綴為 /
# 模板放在 frontstage/templates/frontstage/ 底下，render 時寫 'frontstage/xxx.html'
frontstage_bp = Blueprint('frontstage', __name__, template_folder='../templates')


@frontstage_bp.route('/')
def index():
    return render_template('base.html', message='前台首頁（建置中）')
