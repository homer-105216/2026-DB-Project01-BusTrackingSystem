from flask import Blueprint, abort, redirect, render_template, request, url_for


backstage_bp = Blueprint('backstage', __name__, template_folder='../templates')

PAGE_TEMPLATES = {
    'overview': 'index',
    'members': 'members',
    'routes': 'routes',
    'stations': 'stations',
    'stops': 'stops',
    'bus-types': 'bus_types',
    'buses': 'buses',
    'trips': 'trips',
    'dispatch': 'dispatch',
    'stop-times': 'stop_times',
    'analysis': 'analysis',
}


@backstage_bp.route('/login', methods=['GET', 'POST'])
def login():
    # 介面預覽：不查詢資料庫、不建立登入狀態，也不限制後台存取。
    message = None
    if request.method == 'POST':
        message = '目前尚未串接帳號驗證，請點下方「開啟後台」繼續開發。'
    return render_template('backstage/login.html', preview_message=message,
                           identifier=request.form.get('identifier', '').strip())


@backstage_bp.route('/')
def index():
    return render_template('backstage/index.html', page='overview')


@backstage_bp.route('/<page>')
def console(page):
    if page == 'stop-times':
        return redirect(url_for('backstage.console', page='stops'))
    if page not in PAGE_TEMPLATES or page == 'overview':
        abort(404)
    return render_template(f'backstage/{PAGE_TEMPLATES[page]}.html', page=page)
