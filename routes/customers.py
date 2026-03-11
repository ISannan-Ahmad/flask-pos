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
    analytics = CustomerController.get_customer_analytics(customer_id)
    from controllers.product_controller import ProductController
    distributors = ProductController.get_all_distributors()
    return render_template('customer_detail.html', customer=customer, analytics=analytics, distributors=distributors)

@customers_bp.route('/<int:customer_id>/payment', methods=['POST'])
@login_required
@role_required('admin')
def account_payment(customer_id):
    amount = request.form.get('amount')
    payment_method = request.form.get('payment_method')
    notes = request.form.get('notes')
    payment_destination = request.form.get('payment_destination', 'business')
    supplier_id = request.form.get('supplier_id')
    
    result = CustomerController.apply_account_payment(
        customer_id=customer_id, 
        amount=amount, 
        payment_method=payment_method, 
        notes=notes,
        payment_destination=payment_destination,
        supplier_id=supplier_id
    )
    
    # Old signature returned 2 elements, new returns 3
    if len(result) == 3:
        success, message, txn_id = result
    else:
        success, message = result
        txn_id = None
        
    if success:
        flash(message, 'success')
        if payment_destination == 'supplier' and txn_id:
            return redirect(url_for('customers.settlement_receipt', txn_id=txn_id))
    else:
        flash(message, 'danger')
        
    return redirect(url_for('customers.detail', customer_id=customer_id))

@customers_bp.route('/settlement_receipt/<int:txn_id>')
@login_required
@role_required('admin')
def settlement_receipt(txn_id):
    from models import CustomerTransaction
    from extensions import db
    txn = db.session.get(CustomerTransaction, txn_id)
    if not txn or txn.transaction_type != 'payment':
        flash('Receipt not found', 'danger')
        return redirect(url_for('customers.index'))
        
    supplier_name = txn.reference.replace("Third-Party Payment to ", "") if "Third-Party Payment to " in (txn.reference or "") else "Supplier"
    return render_template('settlement_receipt.html', txn=txn, supplier_name=supplier_name)
