from flask import Blueprint, render_template, abort

backstage_bp = Blueprint('backstage', __name__, template_folder='../templates')


@backstage_bp.route('/')
def index():
    return render_template('backstage/console.html', page='overview')


@backstage_bp.route('/<page>')
def console(page):
    if page not in {'routes', 'stations', 'stops', 'bus-types', 'buses', 'trips', 'dispatch', 'stop-times', 'analysis'}:
        abort(404)
    return render_template('backstage/console.html', page=page)
