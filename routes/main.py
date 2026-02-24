from flask import Blueprint, render_template
from flask_login import login_required, current_user
from controllers.main_controller import MainController

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required
def dashboard():
    if current_user.role == 'admin':
        data = MainController.get_admin_dashboard_data()
        return render_template('dashboard_admin.html', **data)
    else:
        data = MainController.get_staff_dashboard_data(current_user.id)
        return render_template('dashboard_staff.html', **data)
