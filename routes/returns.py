from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from utils import role_required
from models import Order, PurchaseOrder, Product
from controllers.return_controller import ReturnController

from extensions import db
from datetime import datetime

returns_bp = Blueprint('returns', __name__)

@returns_bp.route('/customer')
@login_required
@role_required('admin')
def customer_returns():
    query = request.args.get('q', '')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # Base query for approved orders that are NOT returns themselves
    orders_q = Order.query.filter(Order.status == 'approved', Order.order_type != 'return')

    if query:
        # Search by order ID or Customer Name
        orders_q = orders_q.filter(
            db.or_(
                Order.id.cast(db.String).ilike(f'%{query}%'),
                Order.customer_name.ilike(f'%{query}%')
            )
        )

    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            orders_q = orders_q.filter(Order.created_at >= start_dt)
        except ValueError:
            pass

    if end_date:
        try:
            # Include the entire end day
            end_dt = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            orders_q = orders_q.filter(Order.created_at <= end_dt)
        except ValueError:
            pass

    orders = orders_q.order_by(Order.created_at.desc()).all()
    past_returns = ReturnController.get_customer_returns()
    return render_template('customer_returns.html', orders=orders, past_returns=past_returns, q=query, start_date=start_date, end_date=end_date)

@returns_bp.route('/supplier')
@login_required
@role_required('admin')
def supplier_returns():
    query = request.args.get('q', '')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    pos_q = PurchaseOrder.query.filter_by(status='received')

    if query:
        pos_q = pos_q.join(PurchaseOrder.distributor).filter(
            db.or_(
                PurchaseOrder.id.cast(db.String).ilike(f'%{query}%'),
                db.text('distributors.name ILIKE :q').bindparams(q=f'%{query}%')
            )
        )

    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            pos_q = pos_q.filter(PurchaseOrder.created_at >= start_dt)
        except ValueError:
            pass

    if end_date:
        try:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            pos_q = pos_q.filter(PurchaseOrder.created_at <= end_dt)
        except ValueError:
            pass

    pos = pos_q.order_by(PurchaseOrder.created_at.desc()).all()
    past_returns = ReturnController.get_supplier_returns()
    return render_template('supplier_returns.html', pos=pos, past_returns=past_returns, q=query, start_date=start_date, end_date=end_date)

@returns_bp.route('/defective')
@login_required
@role_required('admin')
def defective_products():
    defective = ReturnController.get_defective_inventory()
    return render_template('defective_products.html', defective_inventory=defective)

@returns_bp.route('/process_customer', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def process_customer():
    if request.method == 'POST':
        success, message, return_id = ReturnController.process_customer_return(request.form, current_user.id)
        if success:
            flash(message, 'success')
            return redirect(url_for('returns.receipt', type='customer', r_id=return_id))
        else:
            flash(message, 'danger')
            return redirect(url_for('returns.customer_returns'))
            
    # For GET, we want to allow searching for an order and selecting a product from it
    o_id = request.args.get('order_id')
    if not o_id:
        flash('Must provide an order_id', 'warning')
        return redirect(url_for('returns.customer_returns'))
        
    order = db.session.get(Order, o_id)
    if not order or order.status != 'approved' or order.order_type == 'return':
        flash('Invalid order for return', 'danger')
        return redirect(url_for('returns.customer_returns'))
        
    # Pass products mapping so template knows what items are in what order
    order_items = {}
    order_items[order.id] = [{'id': i.product.id, 'name': i.product.name, 'qty': i.quantity, 'price': float(i.price)} for i in order.items]
        
    return render_template('process_return_customer.html', order=order, order_items=order_items)

@returns_bp.route('/process_supplier', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def process_supplier():
    if request.method == 'POST':
        success, message, return_id = ReturnController.process_supplier_return(request.form, current_user.id)
        if success:
            flash(message, 'success')
            return redirect(url_for('returns.receipt', type='supplier', r_id=return_id))
        else:
            flash(message, 'danger')
            return redirect(url_for('returns.supplier_returns'))
            
    po_id = request.args.get('po_id')
    if not po_id:
        flash('Must provide a po_id', 'warning')
        return redirect(url_for('returns.supplier_returns'))
        
    po = db.session.get(PurchaseOrder, po_id)
    if not po or po.status != 'received':
         flash('Invalid purchase order for return', 'danger')
         return redirect(url_for('returns.supplier_returns'))
         
    po_items = {}
    po_items[po.id] = []
    for i in po.items:
        # Constraint logic: max return qty = min(originally purchased, currently in stock)
        max_return = min(i.quantity, i.product.stock_quantity)
        if max_return > 0:
             po_items[po.id].append({'id': i.product.id, 'name': i.product.name, 'qty': max_return, 'price': float(i.unit_cost)})
        
    return render_template('process_return_supplier.html', po=po, po_items=po_items)

@returns_bp.route('/receipt/<type>/<int:r_id>')
@login_required
@role_required('admin')
def receipt(type, r_id):
    if type == 'customer':
        return_order = Order.query.get_or_404(r_id)
        return render_template('return_receipt_customer.html', return_order=return_order)
    elif type == 'supplier':
        return_po = PurchaseOrder.query.get_or_404(r_id)
        return render_template('return_receipt_supplier.html', return_po=return_po)
    else:
        flash('Invalid return type', 'danger')
        return redirect(url_for('main.dashboard'))
