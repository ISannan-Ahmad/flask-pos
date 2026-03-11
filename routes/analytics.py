from flask import Blueprint, render_template, request, Response, send_file
from flask_login import login_required
from utils import role_required
from datetime import datetime
from controllers.analytics_controller import AnalyticsController
from controllers.reports_controller import ReportsController
from models import CashTransaction, StockMovement
from extensions import db

analytics_bp = Blueprint('analytics', __name__)


@analytics_bp.route('/')
@login_required
@role_required('admin')
def dashboard():
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


@analytics_bp.route('/monthly-report')
@login_required
@role_required('admin')
def monthly_report():
    now = datetime.now()
    year = request.args.get('year', now.year, type=int)
    month = request.args.get('month', now.month, type=int)

    data = ReportsController.get_monthly_report(year, month)

    return render_template('monthly_report.html',
                           report=data,
                           selected_year=year,
                           selected_month=month,
                           years=range(2020, now.year + 2),
                           months=range(1, 13),
                           month_names=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                                        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])


@analytics_bp.route('/monthly-report/download')
@login_required
@role_required('admin')
def download_report():
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)
    fmt = request.args.get('format', 'csv')

    data = ReportsController.get_monthly_report(year, month)
    filename_base = f"report_{data['month_name']}_{year}"

    if fmt == 'csv':
        csv_output = ReportsController.generate_csv(data)
        return Response(
            csv_output,
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={filename_base}.csv'})

    elif fmt == 'excel':
        excel_output = ReportsController.generate_excel(data)
        return send_file(
            excel_output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'{filename_base}.xlsx')

    elif fmt == 'pdf':
        pdf_output = ReportsController.generate_pdf(data)
        return send_file(
            pdf_output,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'{filename_base}.pdf')

    return 'Invalid format', 400


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
    from models import PKT
    data = AnalyticsController.get_payables_data()
    return render_template('payables.html', **data, now=datetime.now(PKT))


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
    from models import Product
    search = request.args.get('search', '').strip()
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    movement_type = request.args.get('movement_type', '')

    query = StockMovement.query.join(Product)

    if search:
        like = f'%{search}%'
        query = query.filter(
            db.or_(Product.name.ilike(like), Product.sku.ilike(like), Product.brand.ilike(like))
        )
    if movement_type:
        query = query.filter(StockMovement.reference_type == movement_type)
    if start_date:
        query = query.filter(StockMovement.timestamp >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        from datetime import timedelta
        query = query.filter(StockMovement.timestamp <= datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1))

    movements = query.order_by(StockMovement.timestamp.desc()).limit(300).all()
    return render_template('stock_movements.html',
                           movements=movements,
                           search=search,
                           start_date=start_date,
                           end_date=end_date,
                           movement_type=movement_type)
