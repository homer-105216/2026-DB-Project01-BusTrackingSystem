from flask import Blueprint, abort, redirect, render_template, url_for

backstage_bp = Blueprint('backstage', __name__, template_folder='../templates')

PAGE_TEMPLATES = {
    'overview': 'index',
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
