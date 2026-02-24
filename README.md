# 🚗 Suzuki Auto — Flask POS System

A full-featured **Point of Sale & Business Management System** built with Flask, designed for auto spare parts dealerships. Includes inventory management, sales & credit tracking, purchase orders, expense management, and financial analytics.

---

## ✨ Features

| Module | Description |
|--------|-------------|
| **Point of Sale** | Create draft orders (staff) → Admin approves & sets prices |
| **Inventory** | Full product catalog with SKU, part numbers, vehicle compatibility |
| **Restocking** | Quick restock from product page with WAC (Weighted Average Cost) recalculation |
| **Customers** | Customer accounts with credit tracking and FIFO payment allocation |
| **Distributors** | Supplier management with accounts payable ledger |
| **Purchases** | Purchase order lifecycle: create → receive → pay |
| **Expenses** | Track operating costs (salaries, bills, utilities) |
| **Cash Book** | Full cash inflow/outflow ledger with running balances |
| **Analytics** | Revenue, profit, expenses, monthly charts, top products/distributors |
| **Stock Movements** | Audit log for all inventory changes |
| **Role-Based Access** | Admin vs. Staff permissions enforced on all routes |

---

## 🏗️ Project Structure

```
flask_pos/
├── app.py                  # App factory & database seed
├── extensions.py           # Flask extensions (SQLAlchemy, LoginManager)
├── models.py               # All database models
├── utils.py                # role_required decorator
├── requirements.txt        # Python dependencies
│
├── routes/                 # Blueprints (URL routing only)
│   ├── __init__.py         # Blueprint registration
│   ├── auth.py             # Login / Logout
│   ├── main.py             # Dashboard
│   ├── products.py         # Inventory routes
│   ├── sales.py            # Sales order routes
│   ├── purchases.py        # Purchase order routes
│   ├── customers.py        # Customer account routes
│   ├── distributors.py     # Distributor routes
│   ├── expenses.py         # Expense routes
│   └── analytics.py        # Analytics & reports
│
├── controllers/            # Business logic layer
│   ├── product_controller.py
│   ├── sales_controller.py
│   ├── purchases_controller.py
│   ├── customer_controller.py
│   ├── distributors_controller.py
│   ├── expenses_controller.py
│   ├── main_controller.py
│   └── analytics_controller.py
│
└── templates/              # Jinja2 HTML templates
    ├── base.html           # Layout with sidebar navigation
    └── *.html              # Feature-specific pages
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- pip

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/ISannan-Ahmad/flask-pos.git
cd flask_pos

# 2. Create and activate a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the application
python app.py
```

The app will be available at **http://127.0.0.1:5000**

On first run, the database is automatically created and seeded with:
- **Admin** account: `admin` / `admin123`
- **Staff** account: `staff` / `staff123`
- 2 sample distributors and 3 sample products

---

## 🔐 User Roles

| Role | Permissions |
|------|-------------|
| **Admin** | Full access — approve orders, set prices, manage inventory, view all reports and finances |
| **Staff** | Create draft orders, view product catalog, view own order history |

---

## 🗄️ Database Models

```
User ──── Order ──── OrderItem ──── Product
           │                         │
           └── CustomerTransaction   └── PurchaseOrderItem ── PurchaseOrder
                                                                    │
Customer ─────────────────────────────────────────────── Distributor
                                                                    │
                                                     SupplierTransaction

CashTransaction   StockMovement   Expense   AuditLog
```

---

## ⚙️ Configuration

Edit `app.py` to change these settings before deploying:

```python
app.config['SECRET_KEY'] = 'your-secure-secret-key'          # Change this!
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pos.db'    # Or use PostgreSQL
```

---

## 📦 Dependencies

```
Flask
Flask-SQLAlchemy
Flask-Login
Werkzeug
```

See `requirements.txt` for pinned versions.

---

## 📸 Key Workflows

### Creating a Sale
1. Staff logs in → **Point of Sale** → selects products & quantities → creates a **draft order**
2. Admin reviews the draft → sets selling prices → **approves** the order
3. Stock is deducted, ledgers are updated, receipt is generated

### Restocking Inventory
1. Admin → Product Detail → **Quick Restock**
2. Enters quantity, new cost price, and optional payment amount
3. System creates a Purchase Order, updates stock using **Weighted Average Cost**, and logs to the supplier ledger

### Tracking Credit Sales
1. Order is marked as **Credit Sale** at creation
2. Customer balance tracks outstanding receivables
3. Admin records payments via **Customer Account** page — payments are automatically allocated FIFO to oldest invoices

---

## 📄 License

This project is for internal business use. All rights reserved.
