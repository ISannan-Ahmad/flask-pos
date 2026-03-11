from flask import Blueprint, render_template
from flask_login import login_required, current_user
from utils import role_required
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

@main_bp.route('/low-stock')
@login_required
@role_required('admin')
def low_stock():
    products = MainController.get_low_stock_products()
    return render_template('low_stock.html', products=products)

@main_bp.route('/pending-pos')
@login_required
@role_required('admin')
def pending_pos():
    orders = MainController.get_pending_orders()
    return render_template('pending_pos.html', orders=orders)

@main_bp.route('/api/check-new-orders')
def api_check_new_orders():
    from flask import jsonify, request
    
    # Check if the user is authenticated via session
    if not current_user.is_authenticated or current_user.role != 'admin':
        # Alternatively, check for an Authorization header if we need token auth
        # auth_header = request.headers.get('Authorization')
        # if not auth_header or auth_header != 'Bearer YOUR_SECRET_TOKEN':
        return jsonify({'error': 'Unauthorized'}), 401
        
    last_check = request.args.get('last_check')
    data = MainController.check_new_orders(last_check)
    return jsonify(data)

