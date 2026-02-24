from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from utils import role_required
from controllers.customer_controller import CustomerController

customers_bp = Blueprint('customers', __name__)

@customers_bp.route('/', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def index():
    if request.method == 'POST':
        success, message = CustomerController.create_customer(request.form)
        flash(message, 'success' if success else 'danger')
        return redirect(url_for('customers.index'))
        
    customers = CustomerController.get_all_customers()
    return render_template('customers.html', customers=customers)

@customers_bp.route('/<int:customer_id>')
@login_required
@role_required('admin')
def detail(customer_id):
    customer = CustomerController.get_customer(customer_id)
    if not customer:
        flash("Customer not found", "danger")
        return redirect(url_for('customers.index'))
    return render_template('customer_detail.html', customer=customer)

@customers_bp.route('/<int:customer_id>/payment', methods=['POST'])
@login_required
@role_required('admin')
def account_payment(customer_id):
    amount = request.form.get('amount')
    payment_method = request.form.get('payment_method')
    notes = request.form.get('notes')
    
    success, message = CustomerController.apply_account_payment(
        customer_id=customer_id, 
        amount=amount, 
        payment_method=payment_method, 
        notes=notes
    )
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('customers.detail', customer_id=customer_id))
