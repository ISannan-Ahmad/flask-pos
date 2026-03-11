from models import (Order, PurchaseOrder, Product, Distributor, Customer,
                     OrderItem, CustomerTransaction, SupplierTransaction,
                     Expense, CashTransaction, EmployeePayment, PKT)
from extensions import db
from sqlalchemy import func, extract
from datetime import datetime, timedelta


class AnalyticsController:
    @staticmethod
    def get_dashboard_metrics(year, month):
        # Base queries
        sales_query = Order.query.filter(Order.status == 'approved')
        purchases_query = PurchaseOrder.query.filter(PurchaseOrder.status == 'received')
        expenses_query = Expense.query
        staff_query = EmployeePayment.query

        if month:
            sales_query = sales_query.filter(
                extract('year', Order.created_at) == year,
                extract('month', Order.created_at) == month)
            purchases_query = purchases_query.filter(
                extract('year', PurchaseOrder.created_at) == year,
                extract('month', PurchaseOrder.created_at) == month)
            expenses_query = expenses_query.filter(
                extract('year', Expense.expense_date) == year,
                extract('month', Expense.expense_date) == month)
            staff_query = staff_query.filter(
                extract('year', EmployeePayment.date) == year,
                extract('month', EmployeePayment.date) == month)

        # Sales metrics
        total_revenue = float(sales_query.with_entities(func.sum(Order.total_amount)).scalar() or 0)
        gross_profit = float(sales_query.with_entities(func.sum(Order.total_profit)).scalar() or 0)
        total_orders = sales_query.count()

        # Cash vs Credit breakdown
        cash_query = sales_query.filter(Order.order_type == 'sale')
        credit_query = sales_query.filter(Order.order_type == 'credit_sale')

        cash_revenue = float(cash_query.with_entities(func.sum(Order.total_amount)).scalar() or 0)
        cash_count = cash_query.count()
        cash_profit = float(cash_query.with_entities(func.sum(Order.total_profit)).scalar() or 0)

        credit_revenue = float(credit_query.with_entities(func.sum(Order.total_amount)).scalar() or 0)
        credit_count = credit_query.count()
        credit_profit = float(credit_query.with_entities(func.sum(Order.total_profit)).scalar() or 0)

        # Returns metrics
        returns_query = sales_query.filter(Order.order_type == 'return')
        total_returns_amount = float(returns_query.with_entities(func.sum(func.abs(Order.total_amount))).scalar() or 0)
        total_returns_count = returns_query.count()

        # Expense metrics
        total_expenses = float(expenses_query.with_entities(func.sum(Expense.amount)).scalar() or 0)

        # Staff expenses
        total_staff_expenses = float(staff_query.with_entities(func.sum(EmployeePayment.amount)).scalar() or 0)

        # Purchase metrics
        total_purchases = float(purchases_query.with_entities(func.sum(PurchaseOrder.total_amount)).scalar() or 0)

        # Net Profit = Gross Profit (Profit from sales) - Expenses - Staff Expenses
        net_profit = gross_profit - total_expenses - total_staff_expenses

        # Receipts collected (customer payments)
        receipts_query = CustomerTransaction.query.filter(
            CustomerTransaction.transaction_type == 'payment')
        if month:
            receipts_query = receipts_query.filter(
                extract('year', CustomerTransaction.created_at) == year,
                extract('month', CustomerTransaction.created_at) == month)
        total_receipts = float(receipts_query.with_entities(
            func.sum(CustomerTransaction.amount)).scalar() or 0)

        # Outstanding credit
        outstanding_credit = credit_revenue - total_receipts

        # Credit metrics (all-time for summary cards)
        total_receivables = float(
            db.session.query(func.sum(Order.total_amount - Order.amount_paid))
            .filter(Order.status == 'approved',
                    Order.total_amount > Order.amount_paid).scalar() or 0)

        total_payables = float(
            db.session.query(func.sum(PurchaseOrder.total_amount - PurchaseOrder.amount_paid))
            .filter(PurchaseOrder.payment_status != 'paid').scalar() or 0)

        # Top products
        top_products_query = db.session.query(
            Product.name,
            Product.sku,
            func.sum(OrderItem.quantity).label('total_sold'),
            func.sum(OrderItem.quantity * OrderItem.price).label('revenue'),
            func.sum((OrderItem.price - Product.cost_price) * OrderItem.quantity).label('profit')
        ).join(OrderItem).join(Order).filter(Order.status == 'approved')

        if month:
            top_products_query = top_products_query.filter(
                extract('year', Order.created_at) == year,
                extract('month', Order.created_at) == month)

        top_products = top_products_query.group_by(Product.id)\
            .order_by(func.sum(OrderItem.quantity).desc()).limit(10).all()

        # Top distributors
        top_distributors_query = db.session.query(
            Distributor.name,
            func.count(PurchaseOrder.id).label('purchase_count'),
            func.sum(PurchaseOrder.total_amount).label('total_purchases')
        ).join(PurchaseOrder).filter(PurchaseOrder.status == 'received')

        if month:
            top_distributors_query = top_distributors_query.filter(
                extract('year', PurchaseOrder.created_at) == year,
                extract('month', PurchaseOrder.created_at) == month)

        top_distributors = top_distributors_query.group_by(Distributor.id)\
            .order_by(func.sum(PurchaseOrder.total_amount).desc()).limit(5).all()

        # Monthly sales for chart (cash vs credit split)
        monthly_cash = []
        monthly_credit = []
        monthly_profit = []
        monthly_expenses_arr = []
        for m in range(1, 13):
            base = db.session.query(func.sum(Order.total_amount))\
                .filter(Order.status == 'approved',
                        extract('year', Order.created_at) == year,
                        extract('month', Order.created_at) == m)
            cash_m = float(base.filter(Order.order_type == 'sale').scalar() or 0)
            credit_m = float(base.filter(Order.order_type == 'credit_sale').scalar() or 0)
            monthly_cash.append(cash_m)
            monthly_credit.append(credit_m)

            # Monthly revenue and gross profit
            rev_m = cash_m + credit_m
            
            # Monthly gross profit (profit from sales)
            gross_m = float(base.with_entities(func.sum(Order.total_profit)).scalar() or 0)

            # Monthly expenses
            exp_m = float(db.session.query(func.sum(Expense.amount))
                          .filter(extract('year', Expense.expense_date) == year,
                                  extract('month', Expense.expense_date) == m).scalar() or 0)

            # Monthly staff expenses
            staff_m = float(db.session.query(func.sum(EmployeePayment.amount))
                            .filter(extract('year', EmployeePayment.date) == year,
                                    extract('month', EmployeePayment.date) == m).scalar() or 0)

            monthly_expenses_arr.append(exp_m + staff_m)
            monthly_profit.append(gross_m - exp_m - staff_m)

        # Expense breakdown by category
        expense_breakdown = db.session.query(
            Expense.category,
            func.sum(Expense.amount).label('total')
        )
        if month:
            expense_breakdown = expense_breakdown.filter(
                extract('year', Expense.expense_date) == year,
                extract('month', Expense.expense_date) == month)
        expense_breakdown = expense_breakdown.group_by(Expense.category)\
            .order_by(func.sum(Expense.amount).desc()).all()

        expense_categories = [e.category for e in expense_breakdown]
        expense_amounts = [float(e.total) for e in expense_breakdown]

        return {
            'total_revenue': total_revenue,
            'gross_profit': gross_profit,
            'net_profit': net_profit,
            'total_expenses': total_expenses,
            'total_staff_expenses': total_staff_expenses,
            'total_orders': total_orders,
            'cash_revenue': cash_revenue,
            'cash_count': cash_count,
            'cash_profit': cash_profit,
            'credit_revenue': credit_revenue,
            'credit_count': credit_count,
            'credit_profit': credit_profit,
            'total_returns_amount': total_returns_amount,
            'total_returns_count': total_returns_count,
            'total_purchases': total_purchases,
            'total_receivables': total_receivables,
            'total_payables': total_payables,
            'total_receipts': total_receipts,
            'outstanding_credit': outstanding_credit,
            'top_products': top_products,
            'top_distributors': top_distributors,
            'monthly_cash': monthly_cash,
            'monthly_credit': monthly_credit,
            'monthly_profit': monthly_profit,
            'monthly_expenses': monthly_expenses_arr,
            'expense_categories': expense_categories,
            'expense_amounts': expense_amounts,
        }

    @staticmethod
    def get_aging_data():
        today = datetime.now(PKT).date()

        receivables = Order.query.filter(Order.status == 'approved')\
            .filter(Order.total_amount > Order.amount_paid).all()

        aging_receivables = {
            '0-30': [], '31-60': [], '61-90': [], '90+': []
        }

        for order in receivables:
            days_due = (today - order.created_at.date()).days
            remaining = order.total_amount - order.amount_paid

            item = {
                'id': order.id,
                'customer': order.customer_name or f"Order #{order.id}",
                'amount': remaining,
                'date': order.created_at.strftime('%Y-%m-%d'),
                'days_due': days_due
            }

            if days_due <= 30:
                aging_receivables['0-30'].append(item)
            elif days_due <= 60:
                aging_receivables['31-60'].append(item)
            elif days_due <= 90:
                aging_receivables['61-90'].append(item)
            else:
                aging_receivables['90+'].append(item)

        payables = PurchaseOrder.query.filter(PurchaseOrder.payment_status != 'paid')\
            .filter(PurchaseOrder.total_amount > PurchaseOrder.amount_paid).all()

        aging_payables = {
            '0-30': [], '31-60': [], '61-90': [], '90+': []
        }

        for po in payables:
            days_since = (today - po.created_at.date()).days
            remaining = po.total_amount - po.amount_paid

            item = {
                'id': po.id,
                'distributor': po.distributor.name,
                'amount': remaining,
                'date': po.created_at.strftime('%Y-%m-%d'),
                'days': days_since
            }

            if days_since <= 30:
                aging_payables['0-30'].append(item)
            elif days_since <= 60:
                aging_payables['31-60'].append(item)
            elif days_since <= 90:
                aging_payables['61-90'].append(item)
            else:
                aging_payables['90+'].append(item)

        return aging_receivables, aging_payables

    @staticmethod
    def get_ledger_data(transaction_type, start_date, end_date):
        query = CashTransaction.query

        if transaction_type != 'all':
            query = query.filter_by(transaction_type=transaction_type)

        if start_date:
            query = query.filter(CashTransaction.created_at >= datetime.strptime(start_date, '%Y-%m-%d'))
        if end_date:
            query = query.filter(CashTransaction.created_at <= datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1))

        transactions = query.order_by(CashTransaction.created_at.asc()).all()

        balance = 0
        result = []
        for t in transactions:
            if t.transaction_type == 'in':
                balance += float(t.amount)
            else:
                balance -= float(t.amount)
            result.append({
                'id': t.id,
                'transaction_type': t.transaction_type,
                'amount': t.amount,
                'source': t.source,
                'description': t.description,
                'created_at': t.created_at,
                'creator_username': t.creator.username if t.creator else '—',
                'running_balance': balance
            })

        return reversed(result)

    @staticmethod
    def get_receivables_data():
        """Returns registered customer outstanding balances only."""
        all_customers = Customer.query.all()
        debtors = [c for c in all_customers if c.balance > 0]
        total_registered = sum(c.balance for c in debtors)

        return {
            'debtors': debtors,
            'total_registered': total_registered,
            'grand_total': float(total_registered),
        }

    @staticmethod
    def get_payables_data():
        """Returns distributor outstanding balances with per-PO breakdown."""
        all_distributors = Distributor.query.all()
        creditors = []
        for d in all_distributors:
            if d.balance > 0:
                outstanding_pos = PurchaseOrder.query.filter(
                    PurchaseOrder.distributor_id == d.id,
                    PurchaseOrder.payment_status != 'paid'
                ).order_by(PurchaseOrder.created_at.desc()).all()
                creditors.append({
                    'distributor': d,
                    'balance': d.balance,
                    'outstanding_pos': outstanding_pos,
                })
        total_payable = sum(c['balance'] for c in creditors)
        return {
            'creditors': creditors,
            'total_payable': total_payable,
        }

    @staticmethod
    def get_ledger_entries(transaction_type, start_date, end_date):
        """Returns unified CustomerTransaction + SupplierTransaction ledger with running balance."""
        ct_query = CustomerTransaction.query
        st_query = SupplierTransaction.query

        if transaction_type == 'customer':
            st_query = st_query.filter(False)
        elif transaction_type == 'supplier':
            ct_query = ct_query.filter(False)

        if start_date:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            ct_query = ct_query.filter(CustomerTransaction.created_at >= start_dt)
            st_query = st_query.filter(SupplierTransaction.created_at >= start_dt)
        if end_date:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            ct_query = ct_query.filter(CustomerTransaction.created_at <= end_dt)
            st_query = st_query.filter(SupplierTransaction.created_at <= end_dt)

        customer_txns = ct_query.all()
        supplier_txns = st_query.all()

        entries = []
        for t in customer_txns:
            entries.append({
                'created_at': t.created_at,
                'ledger': 'customer',
                'entity': t.customer.name if t.customer else 'Unknown',
                'entity_id': t.customer_id,
                'transaction_type': t.transaction_type,
                'amount': float(t.amount),
                'reference': t.reference,
                'notes': t.notes,
                'payment_method': t.payment_method,
                'order_id': t.order_id,
                'purchase_order_id': None,
            })
        for t in supplier_txns:
            entries.append({
                'created_at': t.created_at,
                'ledger': 'supplier',
                'entity': t.distributor.name if t.distributor else 'Unknown',
                'entity_id': t.distributor_id,
                'transaction_type': t.transaction_type,
                'amount': float(t.amount),
                'reference': t.reference,
                'notes': t.notes,
                'payment_method': t.payment_method,
                'order_id': None,
                'purchase_order_id': t.purchase_order_id,
            })

        entries.sort(key=lambda x: x['created_at'])

        balance = 0.0
        for e in entries:
            if e['transaction_type'] in ('receivable',):
                balance += e['amount']
            elif e['ledger'] == 'customer' and e['transaction_type'] == 'payment':
                balance -= e['amount']
            elif e['transaction_type'] == 'payable':
                balance -= e['amount']
            elif e['ledger'] == 'supplier' and e['transaction_type'] == 'payment':
                balance += e['amount']
            e['running_balance'] = balance

        total_receivables = float(
            db.session.query(func.sum(CustomerTransaction.amount))
            .filter(CustomerTransaction.transaction_type == 'receivable').scalar() or 0
        ) - float(
            db.session.query(func.sum(CustomerTransaction.amount))
            .filter(CustomerTransaction.transaction_type == 'payment').scalar() or 0
        )
        total_payables = float(
            db.session.query(func.sum(SupplierTransaction.amount))
            .filter(SupplierTransaction.transaction_type == 'payable').scalar() or 0
        ) - float(
            db.session.query(func.sum(SupplierTransaction.amount))
            .filter(SupplierTransaction.transaction_type == 'payment').scalar() or 0
        )

        return {
            'transactions': list(reversed(entries)),
            'total_receivables': max(total_receivables, 0),
            'total_payables': max(total_payables, 0),
        }
