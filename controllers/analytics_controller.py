from models import Order, PurchaseOrder, Product, Distributor, Customer, OrderItem, CustomerTransaction, SupplierTransaction, Expense, CashTransaction
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
        
        if month:
            sales_query = sales_query.filter(extract('year', Order.created_at) == year,
                                            extract('month', Order.created_at) == month)
            purchases_query = purchases_query.filter(extract('year', PurchaseOrder.created_at) == year,
                                                    extract('month', PurchaseOrder.created_at) == month)
            expenses_query = expenses_query.filter(extract('year', Expense.expense_date) == year,
                                                    extract('month', Expense.expense_date) == month)
        
        # Sales metrics
        total_revenue = sales_query.with_entities(func.sum(Order.total_amount)).scalar() or 0
        gross_profit = sales_query.with_entities(func.sum(Order.total_profit)).scalar() or 0
        total_orders = sales_query.count()
        
        # Expense metrics
        total_expenses = expenses_query.with_entities(func.sum(Expense.amount)).scalar() or 0
        
        # Net Profit
        net_profit = gross_profit - total_expenses
        
        # Purchase metrics
        total_purchases = purchases_query.with_entities(func.sum(PurchaseOrder.total_amount)).scalar() or 0
        
        # Credit metrics
        total_receivables = db.session.query(func.sum(Order.total_amount - Order.amount_paid))\
            .filter(Order.status == 'approved')\
            .filter(Order.total_amount > Order.amount_paid).scalar() or 0
            
        total_payables = db.session.query(func.sum(PurchaseOrder.total_amount - PurchaseOrder.amount_paid))\
            .filter(PurchaseOrder.payment_status != 'paid').scalar() or 0
        
        # Top products
        top_products_query = db.session.query(
            Product.name,
            Product.sku,
            func.sum(OrderItem.quantity).label('total_sold'),
            func.sum(OrderItem.quantity * OrderItem.price).label('revenue'),
            func.sum((OrderItem.price - Product.cost_price) * OrderItem.quantity).label('profit')
        ).join(OrderItem).join(Order).filter(Order.status == 'approved')
        
        if month:
            top_products_query = top_products_query.filter(extract('year', Order.created_at) == year,
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
            top_distributors_query = top_distributors_query.filter(extract('year', PurchaseOrder.created_at) == year,
                                                      extract('month', PurchaseOrder.created_at) == month)
        
        top_distributors = top_distributors_query.group_by(Distributor.id)\
            .order_by(func.sum(PurchaseOrder.total_amount).desc()).limit(5).all()
        
        # Monthly sales for chart
        monthly_sales = []
        for m in range(1, 13):
            monthly_revenue = db.session.query(func.sum(Order.total_amount))\
                .filter(Order.status == 'approved',
                       extract('year', Order.created_at) == year,
                       extract('month', Order.created_at) == m).scalar() or 0
            monthly_sales.append(monthly_revenue)
            
        return {
            'total_revenue': total_revenue,
            'gross_profit': gross_profit,
            'net_profit': net_profit,
            'total_expenses': total_expenses,
            'total_orders': total_orders,
            'total_purchases': total_purchases,
            'total_receivables': total_receivables,
            'total_payables': total_payables,
            'top_products': top_products,
            'top_distributors': top_distributors,
            'monthly_sales': monthly_sales
        }

    @staticmethod
    def get_aging_data():
        today = datetime.utcnow().date()
        
        receivables = Order.query.filter(Order.status == 'approved')\
            .filter(Order.total_amount > Order.amount_paid).all()
        
        aging_receivables = {
            '0-30': [],
            '31-60': [],
            '61-90': [],
            '90+': []
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
            '0-30': [],
            '31-60': [],
            '61-90': [],
            '90+': []
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
        # We handle general cash book here
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
            
        return reversed(result) # return latest first but with correct running balance

    @staticmethod
    def get_receivables_data():
        """Returns registered customer outstanding balances + walk-in unpaid orders."""
        # Section 1: Registered customers with a positive balance (via CustomerTransaction ledger)
        all_customers = Customer.query.all()
        debtors = [c for c in all_customers if c.balance > 0]
        total_registered = sum(c.balance for c in debtors)

        # Section 2: Walk-in / unregistered orders that are not fully paid
        walkin_orders = Order.query.filter(
            Order.status == 'approved',
            Order.customer_id == None,
            Order.total_amount > Order.amount_paid
        ).order_by(Order.created_at.desc()).all()
        total_walkin = sum(float(o.total_amount) - float(o.amount_paid) for o in walkin_orders)

        grand_total = float(total_registered) + total_walkin

        return {
            'debtors': debtors,
            'walkin_orders': walkin_orders,
            'total_registered': total_registered,
            'total_walkin': total_walkin,
            'grand_total': grand_total,
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
        from datetime import datetime, timedelta

        # Build customer transactions query
        ct_query = CustomerTransaction.query
        st_query = SupplierTransaction.query

        if transaction_type == 'customer':
            st_query = st_query.filter(False)  # exclude supplier entries
        elif transaction_type == 'supplier':
            ct_query = ct_query.filter(False)  # exclude customer entries

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

        # Normalise into a unified list
        entries = []
        for t in customer_txns:
            entries.append({
                'created_at': t.created_at,
                'ledger': 'customer',
                'entity': t.customer.name if t.customer else 'Unknown',
                'entity_id': t.customer_id,
                'transaction_type': t.transaction_type,   # 'receivable' or 'payment'
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
                'transaction_type': t.transaction_type,   # 'payable' or 'payment'
                'amount': float(t.amount),
                'reference': t.reference,
                'notes': t.notes,
                'payment_method': t.payment_method,
                'order_id': None,
                'purchase_order_id': t.purchase_order_id,
            })

        # Sort by date ascending for running balance, then reverse for display
        entries.sort(key=lambda x: x['created_at'])

        # Running balance: receivable/payable increases what is owed, payment decreases it
        balance = 0.0
        for e in entries:
            if e['transaction_type'] in ('receivable',):   # customer owes us more
                balance += e['amount']
            elif e['ledger'] == 'customer' and e['transaction_type'] == 'payment':
                balance -= e['amount']                      # customer paid us
            elif e['transaction_type'] == 'payable':        # we owe supplier more
                balance -= e['amount']
            elif e['ledger'] == 'supplier' and e['transaction_type'] == 'payment':
                balance += e['amount']                      # we paid supplier
            e['running_balance'] = balance

        # Compute summary totals (unfiltered for summary cards)
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
