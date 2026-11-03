from flask import Blueprint, render_template, request, redirect, url_for

# 前台 Blueprint，網址前綴為 /
# 模板放在 frontstage/templates/frontstage/ 底下，render 時寫 'frontstage/xxx.html'
frontstage_bp = Blueprint('frontstage', __name__, template_folder='../templates')


@frontstage_bp.route('/')
def index():
    """前台首頁：展示附近公車、熱門路線與搜尋框（搜尋後直達路線畫面）"""
    keyword = request.args.get('keyword', '').strip()
    if keyword:
        # 首頁搜尋後直接導向路線畫面（依關鍵字匹配示範路線）
        route_map = {
            '100': 'R100',
            '205': 'R205',
            '168': 'R168E',
            '168東': 'R168E',
            '50': 'R50',
            '紅30': 'R-RD30'
        }
        target_id = route_map.get(keyword, 'R100')
        return redirect(url_for('frontstage.route_detail', route_id=target_id))
    return render_template('frontstage/index.html')


@frontstage_bp.route('/route/<route_id>')
def route_detail(route_id):
    return render_template('frontstage/route_detail.html', route_id=route_id)


@frontstage_bp.route('/favorites')
def favorites():
    """我的收藏：查看已收藏路線與站點（未登入按鈕有提示彈窗）"""
    return render_template('frontstage/favorites.html')


@frontstage_bp.route('/login', methods=['GET', 'POST'])
def login():
    """會員登入畫面"""
    return render_template('frontstage/login.html')


@frontstage_bp.route('/register', methods=['GET', 'POST'])
def register():
    """會員註冊畫面"""
    return render_template('frontstage/register.html')


@frontstage_bp.route('/logout')
def logout():
    """會員登出"""
    return redirect(url_for('frontstage.index'))


@frontstage_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    """帳號設定畫面（修改 username、email、password）"""
    return render_template('frontstage/profile.html')
