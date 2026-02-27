from flask import Blueprint, render_template, request
from flask_login import login_required
from utils import role_required
from datetime import datetime
from controllers.analytics_controller import AnalyticsController
from models import CashTransaction, StockMovement

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
    data = AnalyticsController.get_receivables_data()
    return render_template('receivables.html', **data)

@analytics_bp.route('/payables')
@login_required
@role_required('admin')
def payables():
    data = AnalyticsController.get_payables_data()
    return render_template('payables.html', **data)

@analytics_bp.route('/ledger')
@login_required
@role_required('admin')
def ledger():
    transaction_type = request.args.get('type', 'all')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    data = AnalyticsController.get_ledger_entries(transaction_type, start_date, end_date)
    return render_template('ledger.html',
                           transactions=data['transactions'],
                           total_receivables=data['total_receivables'],
                           total_payables=data['total_payables'],
                           transaction_type=transaction_type,
                           start_date=start_date or '',
                           end_date=end_date or '')

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

@analytics_bp.route('/aging-report')
@login_required
@role_required('admin')
def aging_report():
    aging_receivables, aging_payables = AnalyticsController.get_aging_data()
    return render_template('aging_report.html',
                           aging_receivables=aging_receivables,
                           aging_payables=aging_payables)

@analytics_bp.route('/stock-movements')
@login_required
@role_required('admin')
def stock_movements():
    movements = StockMovement.query.order_by(StockMovement.timestamp.desc()).limit(200).all()
    return render_template('stock_movements.html', movements=movements)
