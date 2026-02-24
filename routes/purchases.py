from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import Distributor, Product
from utils import role_required
from controllers.purchases_controller import PurchasesController

purchases_bp = Blueprint('purchases', __name__)

@purchases_bp.route('/')
@login_required
@role_required('admin')
def purchase_orders():
    purchases = PurchasesController.get_all_purchases()
    return render_template('purchase_orders.html', purchases=purchases)

@purchases_bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def create_purchase_order():
    if request.method == 'POST':
        success, message, purchase_order = PurchasesController.create_purchase_order(request.form, current_user.id)
        if success:
             flash(message, "success")
             return redirect(url_for('purchases.purchase_order_detail', id=purchase_order.id))
        else:
             flash(message, "danger")
    
    distributors = Distributor.query.all()
    products = Product.query.all()
    return render_template('create_purchase_order.html', distributors=distributors, products=products)

@purchases_bp.route('/<int:id>')
@login_required
@role_required('admin')
def purchase_order_detail(id):
    purchase = PurchasesController.get_purchase_order(id)
    if not purchase:
        flash("Purchase order not found.", "danger")
        return redirect(url_for('purchases.purchase_orders'))
    return render_template('purchase_order_detail.html', purchase=purchase)

@purchases_bp.route('/<int:id>/receive', methods=['POST'])
@login_required
@role_required('admin')
def receive_purchase_order(id):
    success, message = PurchasesController.receive_purchase_order(id)
    if success:
         flash(message, "success")
    else:
         flash(message, "danger" if "not found" in message else "warning")
    return redirect(url_for('purchases.purchase_order_detail', id=id) if "already received" in message or "not found" not in message else url_for('purchases.purchase_orders'))

@purchases_bp.route('/<int:id>/payment', methods=['POST'])
@login_required
@role_required('admin')
def add_purchase_payment(id):
    success, message = PurchasesController.add_purchase_payment(id, request.form, current_user.id)
    if success:
         flash(message, "success")
         return redirect(url_for('purchases.purchase_order_detail', id=id))
    else:
         flash(message, "danger")
         if "not found" in message:
             return redirect(url_for('purchases.purchase_orders'))
         return redirect(url_for('purchases.purchase_order_detail', id=id))

@purchases_bp.route('/<int:id>/receipt')
@login_required
@role_required('admin')
def purchase_receipt(id):
    purchase = PurchasesController.get_purchase_order(id)
    if not purchase:
        flash("Purchase order not found.", "danger")
        return redirect(url_for('purchases.purchase_orders'))
    return render_template('purchase_receipt.html', purchase=purchase)
