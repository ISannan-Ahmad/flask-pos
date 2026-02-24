from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import Product, Customer
from utils import role_required
from controllers.sales_controller import SalesController

sales_bp = Blueprint('sales', __name__)

@sales_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_order():
    all_products = Product.query.filter_by(is_active=True).all()
    # Ideally should only show active customers or handle async search
    all_customers = Customer.query.order_by(Customer.name.asc()).all()
    
    if request.method == 'POST':
        success, message = SalesController.create_order(request.form, current_user.id)
        if success:
             flash(message, "success")
             return redirect(url_for('main.dashboard'))
        else:
             flash(message, "danger" if "Insufficient" in message else "warning")
             return redirect(url_for('sales.create_order'))
    
    return render_template('create_order.html', products=all_products, customers=all_customers)

@sales_bp.route('/orders/<int:order_id>', methods=['GET', 'POST'])
@login_required
def order_detail(order_id):
    order = SalesController.get_order_by_id(order_id)
    if not order:
        flash("Order not found.", "danger")
        return redirect(url_for('main.dashboard'))
        
    # Staff can view their own draft orders, or any order if they are admin
    if current_user.role != 'admin' and (order.status != 'draft' or order.created_by != current_user.id):
        flash("You don't have permission to view that order.", "danger")
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        if current_user.role != 'admin':
            flash("Only administrators can approve orders.", "danger")
            return redirect(url_for('sales.order_detail', order_id=order_id))
            
        success, message = SalesController.approve_order(order_id, request.form, current_user.id)
        if success:
             flash(message, "success")
             return redirect(url_for('sales.receipt', order_id=order_id))
        else:
             flash(message, "danger" if "stock" in message.lower() else "warning")
             if "already approved" in message.lower():
                 return redirect(url_for('main.dashboard'))
             return redirect(url_for('sales.order_detail', order_id=order_id))

    return render_template('order_detail.html', order=order)

@sales_bp.route('/orders/<int:order_id>/payment', methods=['POST'])
@login_required
@role_required('admin')
def add_order_payment(order_id):
    success, message = SalesController.add_order_payment(order_id, request.form, current_user.id)
    if success:
         flash(message, "success")
    else:
         flash(message, "danger")
    return redirect(url_for('sales.order_detail', order_id=order_id))

@sales_bp.route('/receipt/<int:order_id>')
@login_required
@role_required('admin')
def receipt(order_id):
    order = SalesController.get_order_by_id(order_id)
    if not order:
        flash("Order not found.", "danger")
        return redirect(url_for('main.dashboard'))
    return render_template('receipt.html', order=order)

@sales_bp.route('/history')
@login_required
@role_required('admin')
def sales_history():
    orders = SalesController.get_all_orders()
    return render_template('sales_history.html', orders=orders)
