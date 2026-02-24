from flask_login import UserMixin
from datetime import datetime
from extensions import db

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # staff / admin
    full_name = db.Column(db.String(200))
    phone = db.Column(db.String(20))
    
    # Relationships
    created_orders = db.relationship('Order', foreign_keys='Order.created_by', back_populates='creator', lazy=True)
    approved_orders = db.relationship('Order', foreign_keys='Order.approved_by', back_populates='approver', lazy=True)
    created_purchases = db.relationship('PurchaseOrder', foreign_keys='PurchaseOrder.created_by', back_populates='creator', lazy=True)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Distributor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    contact_person = db.Column(db.String(200))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(200))
    address = db.Column(db.Text)
    payment_terms = db.Column(db.Integer, default=30)  # Days
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    products = db.relationship('Product', back_populates='distributor', lazy=True)
    purchase_orders = db.relationship('PurchaseOrder', back_populates='distributor', lazy=True)
    transactions = db.relationship('SupplierTransaction', back_populates='distributor', lazy=True)
    
    @property
    def balance(self):
        """Get current balance with this distributor"""
        credit = db.session.query(db.func.sum(SupplierTransaction.amount))\
            .filter(SupplierTransaction.distributor_id == self.id,
                   SupplierTransaction.transaction_type == 'payable').scalar() or 0
        debit = db.session.query(db.func.sum(SupplierTransaction.amount))\
            .filter(SupplierTransaction.distributor_id == self.id,
                   SupplierTransaction.transaction_type == 'payment').scalar() or 0
        return credit - debit
    
    def __repr__(self):
        return f'<Distributor {self.name}>'

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    credit_limit = db.Column(db.Numeric(12, 2), default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    orders = db.relationship('Order', back_populates='customer', lazy=True)
    transactions = db.relationship('CustomerTransaction', back_populates='customer', lazy=True)
    
    @property
    def balance(self):
        """Get current balance for this customer"""
        receivable = db.session.query(db.func.sum(CustomerTransaction.amount))\
            .filter(CustomerTransaction.customer_id == self.id,
                   CustomerTransaction.transaction_type == 'receivable').scalar() or 0
        payment = db.session.query(db.func.sum(CustomerTransaction.amount))\
            .filter(CustomerTransaction.customer_id == self.id,
                   CustomerTransaction.transaction_type == 'payment').scalar() or 0
        return receivable - payment
        
    def __repr__(self):
        return f'<Customer {self.name}>'

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    sku = db.Column(db.String(50), unique=True)
    stock_quantity = db.Column(db.Integer, default=0)
    cost_price = db.Column(db.Numeric(12, 2))
    selling_price = db.Column(db.Numeric(12, 2))
    distributor_id = db.Column(db.Integer, db.ForeignKey('distributor.id'), nullable=True)
    vehicle_type = db.Column(db.String(100))  # e.g., Car, Motorcycle, Truck
    vehicle_model = db.Column(db.String(100))  # e.g., Civic 2019, Mehran
    part_number = db.Column(db.String(100))  # Original part number
    min_stock_level = db.Column(db.Integer, default=5)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    distributor = db.relationship('Distributor', back_populates='products')
    order_items = db.relationship('OrderItem', back_populates='product', lazy=True)
    purchase_items = db.relationship('PurchaseOrderItem', back_populates='product', lazy=True)
    stock_movements = db.relationship('StockMovement', back_populates='product', lazy=True)
    
    def __repr__(self):
        return f'<Product {self.name}>'

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=True)
    customer_name = db.Column(db.String(200)) # Keep for walk-in cash sales
    customer_phone = db.Column(db.String(20))
    customer_address = db.Column(db.Text)
    status = db.Column(db.String(20), default='draft')  # draft, approved, completed, cancelled
    order_type = db.Column(db.String(20), default='sale')  # sale, credit_sale
    total_amount = db.Column(db.Numeric(12, 2), default=0.0)
    total_profit = db.Column(db.Numeric(12, 2), default=0.0)
    amount_paid = db.Column(db.Numeric(12, 2), default=0.0)
    due_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    customer = db.relationship('Customer', back_populates='orders', lazy=True)
    items = db.relationship('OrderItem', back_populates='order', lazy=True, cascade='all, delete-orphan')
    creator = db.relationship('User', foreign_keys=[created_by], back_populates='created_orders')
    approver = db.relationship('User', foreign_keys=[approved_by], back_populates='approved_orders')
    transactions = db.relationship('CustomerTransaction', back_populates='order', lazy=True)
    
    @property
    def remaining_amount(self):
        return self.total_amount - self.amount_paid
    
    def __repr__(self):
        return f'<Order {self.id}>'

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id', ondelete='CASCADE'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    quantity = db.Column(db.Integer)
    price = db.Column(db.Numeric(12, 2), nullable=True)  # Selling price at time of order
    
    # Relationships
    order = db.relationship('Order', back_populates='items')
    product = db.relationship('Product', back_populates='order_items')
    
    def __repr__(self):
        return f'<OrderItem {self.id}>'

class PurchaseOrder(db.Model):
    """Purchase orders from distributors"""
    id = db.Column(db.Integer, primary_key=True)
    distributor_id = db.Column(db.Integer, db.ForeignKey('distributor.id'))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    status = db.Column(db.String(20), default='pending')  # pending, received, cancelled
    total_amount = db.Column(db.Numeric(12, 2), default=0.0)
    amount_paid = db.Column(db.Numeric(12, 2), default=0.0)
    payment_status = db.Column(db.String(20), default='pending')  # pending, partial, paid
    invoice_number = db.Column(db.String(100))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    received_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    distributor = db.relationship('Distributor', back_populates='purchase_orders')
    creator = db.relationship('User', foreign_keys=[created_by], back_populates='created_purchases')
    items = db.relationship('PurchaseOrderItem', back_populates='purchase_order', lazy=True, cascade='all, delete-orphan')
    transactions = db.relationship('SupplierTransaction', back_populates='purchase_order', lazy=True)
    
    @property
    def remaining_amount(self):
        return self.total_amount - self.amount_paid
    
    def __repr__(self):
        return f'<PurchaseOrder {self.id}>'

class PurchaseOrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    purchase_order_id = db.Column(db.Integer, db.ForeignKey('purchase_order.id', ondelete='CASCADE'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    quantity = db.Column(db.Integer)
    unit_cost = db.Column(db.Numeric(12, 2))  # Purchase price
    total_cost = db.Column(db.Numeric(12, 2))
    
    # Relationships
    purchase_order = db.relationship('PurchaseOrder', back_populates='items')
    product = db.relationship('Product', back_populates='purchase_items')
    
    def __repr__(self):
        return f'<PurchaseOrderItem {self.id}>'

class CustomerTransaction(db.Model):
    """Accounts Receivable Ledger"""
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=True)
    transaction_type = db.Column(db.String(20)) # receivable (implies debt increased), payment (implies debt decreased)
    amount = db.Column(db.Numeric(12, 2))
    payment_method = db.Column(db.String(50)) # cash, bank, etc.
    reference = db.Column(db.String(200))
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    customer = db.relationship('Customer', back_populates='transactions')
    order = db.relationship('Order', back_populates='transactions')
    creator = db.relationship('User', foreign_keys=[created_by])

class SupplierTransaction(db.Model):
    """Accounts Payable Ledger"""
    id = db.Column(db.Integer, primary_key=True)
    distributor_id = db.Column(db.Integer, db.ForeignKey('distributor.id'))
    purchase_order_id = db.Column(db.Integer, db.ForeignKey('purchase_order.id'), nullable=True)
    transaction_type = db.Column(db.String(20)) # payable (implies debt to supplier increased), payment (implies we paid supplier)
    amount = db.Column(db.Numeric(12, 2))
    payment_method = db.Column(db.String(50))
    reference = db.Column(db.String(200))
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    distributor = db.relationship('Distributor', back_populates='transactions')
    purchase_order = db.relationship('PurchaseOrder', back_populates='transactions')
    creator = db.relationship('User', foreign_keys=[created_by])

class CashTransaction(db.Model):
    """Cash Book Ledger (Inflows and Outflows)"""
    id = db.Column(db.Integer, primary_key=True)
    transaction_type = db.Column(db.String(20)) # in, out
    amount = db.Column(db.Numeric(12, 2))
    source = db.Column(db.String(100)) # sales, customer_payment, supplier_payment, expense, manual
    reference_id = db.Column(db.Integer, nullable=True) # ID of the related order, expense, PO
    description = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    creator = db.relationship('User', foreign_keys=[created_by])

class StockMovement(db.Model):
    """Audit log for all stock changes"""
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    quantity_change = db.Column(db.Integer)  # Positive for adding, negative for removing
    quantity_before = db.Column(db.Integer)
    quantity_after = db.Column(db.Integer)
    reference_type = db.Column(db.String(50))  # 'sale', 'purchase_receipt', 'manual_adjustment', 'restock'
    reference_id = db.Column(db.Integer, nullable=True)  # ID of related Order or PurchaseOrder
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    product = db.relationship('Product', back_populates='stock_movements')
    user = db.relationship('User', foreign_keys=[user_id])
    
    def __repr__(self):
        return f'<StockMovement {self.product.name} {self.quantity_change}>'

class Expense(db.Model):
    """Track extra expenses like salaries and bills"""
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False)  # e.g., Salary, Bill, Utilities, Maintenance
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    description = db.Column(db.Text)
    expense_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    creator = db.relationship('User', backref='expenses')
    
    def __repr__(self):
        return f'<Expense {self.category} - Rs. {self.amount}>'

class AuditLog(db.Model):
    """Tracks critical changes in the system"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    action = db.Column(db.String(100)) # e.g. "Update Product Price", "Cancel Order"
    table_name = db.Column(db.String(100))
    record_id = db.Column(db.Integer)
    old_value = db.Column(db.Text, nullable=True)
    new_value = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', foreign_keys=[user_id])
