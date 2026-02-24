from flask import Blueprint, render_template, request
from flask_login import login_required
from utils import role_required
from datetime import datetime
from controllers.analytics_controller import AnalyticsController
from models import Customer, Distributor, CashTransaction, StockMovement

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/')
@login_required
@role_required('admin')
def dashboard():
    # Get date filters
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', None, type=int)
    
    metrics = AnalyticsController.get_dashboard_metrics(year, month)
    
    return render_template('analytics.html',
                           **metrics,
                           selected_year=year,
                           selected_month=month,
                           months=range(1, 13),
                           month_names=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                                       'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])

@analytics_bp.route('/receivables')
@login_required
@role_required('admin')
def receivables():
    customers = Customer.query.all()
    # Filter customers who owe money
    debtors = [c for c in customers if c.balance > 0]
    total_receivable = sum(c.balance for c in debtors)
    return render_template('receivables.html', debtors=debtors, total_receivable=total_receivable)

@analytics_bp.route('/payables')
@login_required
@role_required('admin')
def payables():
    distributors = Distributor.query.all()
    # Filter distributors we owe money
    creditors = [d for d in distributors if d.balance > 0]
    total_payable = sum(d.balance for d in creditors)
    return render_template('payables.html', creditors=creditors, total_payable=total_payable)

@analytics_bp.route('/cashbook')
@login_required
@role_required('admin')
def cashbook():
    transaction_type = request.args.get('type', 'all')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    transactions = AnalyticsController.get_ledger_data(transaction_type, start_date, end_date)
    metrics = AnalyticsController.get_dashboard_metrics(datetime.now().year, None)
    
    return render_template('cashbook.html', 
                         transactions=list(transactions),
                         transaction_type=transaction_type,
                         start_date=start_date,
                         end_date=end_date,
                         total_receivables=metrics.get('total_receivables', 0),
                         total_payables=metrics.get('total_payables', 0))

@analytics_bp.route('/stock-movements')
@login_required
@role_required('admin')
def stock_movements():
    movements = StockMovement.query.order_by(StockMovement.timestamp.desc()).limit(200).all()
    return render_template('stock_movements.html', movements=movements)
