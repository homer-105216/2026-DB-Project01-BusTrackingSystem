from flask import Blueprint, render_template

# 後台 Blueprint，網址前綴為 /backstage
# 模板放在 backstage/templates/backstage/ 底下，render 時寫 'backstage/xxx.html'
backstage_bp = Blueprint('backstage', __name__, template_folder='../templates')


@backstage_bp.route('/')
def index():
    return render_template('base.html', message='後台首頁（建置中）')
