# Suzuki Auto POS — Complete Project Documentation

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Database Schema](#3-database-schema)
4. [User Roles & Access Control](#4-user-roles--access-control)
5. [Application Startup Flow](#5-application-startup-flow)
6. [Module Workflows](#6-module-workflows)
   - [Authentication](#61-authentication)
   - [Sales Order Lifecycle](#62-sales-order-lifecycle)
   - [Purchase Order Lifecycle](#63-purchase-order-lifecycle)
   - [Inventory & Restocking](#64-inventory--restocking)
   - [Customer Account & Payments](#65-customer-account--payments)
   - [Expense Tracking](#66-expense-tracking)
   - [Cash Book & Ledgers](#67-cash-book--ledgers)
   - [Analytics & Reports](#68-analytics--reports)
7. [Data Flow Between Modules](#7-data-flow-between-modules)
8. [Code Architecture](#8-code-architecture)

---

## 1. Project Overview

**Suzuki Auto POS** is a web-based Point of Sale and business management system tailored for auto spare parts dealerships. It is built with the **Flask** micro-framework following a clean **MVC architecture** with blueprints.

### Core Business Problem It Solves

```mermaid
graph LR
    A[🧑 Customer walks in] --> B[Staff creates Sale Order]
    B --> C[Admin approves & sets prices]
    C --> D[Stock deducted automatically]
    D --> E[Ledgers updated]
    E --> F[Receipt generated]

    G[📦 Stock running low] --> H[Admin creates Purchase Order]
    H --> I[Goods received from Distributor]
    I --> J[Stock updated automatically]
    J --> K[Supplier payable recorded]
```

### Tech Stack

| Layer | Technology |
|-------|------------|
| Backend Framework | Flask (Python) |
| Database ORM | SQLAlchemy |
| Authentication | Flask-Login |
| Frontend | Bootstrap 5, Chart.js, Select2 |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Templating | Jinja2 |

---

## 2. System Architecture

```mermaid
graph TD
    Browser["🌐 Browser (Bootstrap + JS)"]

    subgraph Flask Application
        subgraph Routes["Routes Layer (Blueprints)"]
            R1[auth.py]
            R2[products.py]
            R3[sales.py]
            R4[purchases.py]
            R5[customers.py]
            R6[distributors.py]
            R7[expenses.py]
            R8[analytics.py]
            R9[main.py]
        end

        subgraph Controllers["Controllers Layer (Business Logic)"]
            C1[ProductController]
            C2[SalesController]
            C3[PurchasesController]
            C4[CustomerController]
            C5[DistributorsController]
            C6[ExpensesController]
            C7[AnalyticsController]
            C8[MainController]
        end

        subgraph Models["Models Layer (SQLAlchemy ORM)"]
            M1[User]
            M2[Product]
            M3[Order / OrderItem]
            M4[PurchaseOrder / PurchaseOrderItem]
            M5[Customer / CustomerTransaction]
            M6[Distributor / SupplierTransaction]
            M7[Expense / CashTransaction]
            M8[StockMovement / AuditLog]
        end
    end

    DB[(SQLite / PostgreSQL)]

    Browser --> Routes
    Routes --> Controllers
    Controllers --> Models
    Models --> DB
```

---

## 3. Database Schema

```mermaid
erDiagram
    USER {
        int id PK
        string username
        string password_hash
        string role
        string full_name
        string phone
    }

    CUSTOMER {
        int id PK
        string name
        string phone
        decimal credit_limit
        datetime created_at
    }

    DISTRIBUTOR {
        int id PK
        string name
        string contact_person
        string phone
        int payment_terms
    }

    PRODUCT {
        int id PK
        string name
        string sku
        int stock_quantity
        decimal cost_price
        decimal selling_price
        int distributor_id FK
        string vehicle_type
        string vehicle_model
        string part_number
        int min_stock_level
        bool is_active
    }

    ORDER {
        int id PK
        int created_by FK
        int approved_by FK
        int customer_id FK
        string status
        string order_type
        decimal total_amount
        decimal amount_paid
        datetime created_at
    }

    ORDER_ITEM {
        int id PK
        int order_id FK
        int product_id FK
        int quantity
        decimal price
    }

    PURCHASE_ORDER {
        int id PK
        int distributor_id FK
        int created_by FK
        string status
        decimal total_amount
        decimal amount_paid
        string payment_status
        datetime received_at
    }

    PURCHASE_ORDER_ITEM {
        int id PK
        int purchase_order_id FK
        int product_id FK
        int quantity
        decimal unit_cost
        decimal total_cost
    }

    CUSTOMER_TRANSACTION {
        int id PK
        int customer_id FK
        int order_id FK
        string transaction_type
        decimal amount
        string payment_method
    }

    SUPPLIER_TRANSACTION {
        int id PK
        int distributor_id FK
        int purchase_order_id FK
        string transaction_type
        decimal amount
    }

    CASH_TRANSACTION {
        int id PK
        string transaction_type
        decimal amount
        string source
        int reference_id
        string description
    }

    STOCK_MOVEMENT {
        int id PK
        int product_id FK
        int quantity_change
        int quantity_before
        int quantity_after
        string reference_type
    }

    EXPENSE {
        int id PK
        string category
        decimal amount
        datetime expense_date
    }

    USER ||--o{ ORDER : "creates/approves"
    USER ||--o{ PURCHASE_ORDER : creates
    CUSTOMER ||--o{ ORDER : places
    CUSTOMER ||--o{ CUSTOMER_TRANSACTION : has
    DISTRIBUTOR ||--o{ PRODUCT : supplies
    DISTRIBUTOR ||--o{ PURCHASE_ORDER : receives
    DISTRIBUTOR ||--o{ SUPPLIER_TRANSACTION : has
    PRODUCT ||--o{ ORDER_ITEM : in
    PRODUCT ||--o{ PURCHASE_ORDER_ITEM : in
    PRODUCT ||--o{ STOCK_MOVEMENT : tracks
    ORDER ||--o{ ORDER_ITEM : contains
    ORDER ||--o{ CUSTOMER_TRANSACTION : generates
    PURCHASE_ORDER ||--o{ PURCHASE_ORDER_ITEM : contains
    PURCHASE_ORDER ||--o{ SUPPLIER_TRANSACTION : generates
```

---

## 4. User Roles & Access Control

The system has two roles enforced by the `@role_required('admin')` decorator.

```mermaid
graph TD
    Login[Login Page]
    Login --> |Valid credentials| RoleCheck{User Role?}
    RoleCheck --> |admin| AdminDash[Admin Dashboard]
    RoleCheck --> |staff| StaffDash[Staff Dashboard]

    subgraph "Staff Can"
        S1[View product catalog]
        S2[Create draft orders]
        S3[View own order history]
    end

    subgraph "Admin Only"
        A1[Approve orders & set prices]
        A2[Manage products & inventory]
        A3[Create & receive purchase orders]
        A4[Manage distributors & customers]
        A5[View all financial reports]
        A6[Record payments & expenses]
        A7[View cash book & ledgers]
        A8[Access analytics dashboard]
    end

    StaffDash --> S1 & S2 & S3
    AdminDash --> A1 & A2 & A3 & A4 & A5 & A6 & A7 & A8
```

---

## 5. Application Startup Flow

```mermaid
flowchart TD
    Start([python app.py]) --> CreateApp[create_app]
    CreateApp --> Config[Load config\nSECRET_KEY, DB URI]
    Config --> InitExt[Initialize extensions\nSQLAlchemy + LoginManager]
    InitExt --> RegBP[Register 9 Blueprints]
    RegBP --> InitDB[initialize_database]
    InitDB --> CreateTables[db.create_all\nCreate all tables if missing]
    CreateTables --> CheckUsers{Admin user\nexists?}
    CheckUsers --> |No| SeedUsers[Seed admin + staff accounts]
    CheckUsers --> |Yes| CheckDist{Distributor\nexists?}
    SeedUsers --> CheckDist
    CheckDist --> |No| SeedData[Seed 2 distributors\n+ 3 sample products]
    CheckDist --> |Yes| RunServer
    SeedData --> RunServer[app.run debug=True\nhttp://127.0.0.1:5000]
```

---

## 6. Module Workflows

### 6.1 Authentication

```mermaid
sequenceDiagram
    actor User
    participant Browser
    participant AuthRoute as auth.py
    participant DB

    User->>Browser: Navigate to /login
    Browser->>AuthRoute: GET /login
    AuthRoute-->>Browser: Render login form

    User->>Browser: Submit username + password
    Browser->>AuthRoute: POST /login
    AuthRoute->>DB: Query User by username
    DB-->>AuthRoute: User record
    AuthRoute->>AuthRoute: check_password_hash(hash, password)
    
    alt Valid credentials
        AuthRoute->>AuthRoute: login_user(user)
        AuthRoute-->>Browser: Redirect to Dashboard
    else Invalid credentials
        AuthRoute-->>Browser: Flash "Invalid credentials" → Re-render login
    end
```

---

### 6.2 Sales Order Lifecycle

This is the core workflow of the system. Sales require **two steps**: a staff member creates a draft, and an admin approves it.

```mermaid
stateDiagram-v2
    [*] --> Draft: Staff creates order
    Draft --> Approved: Admin sets prices & approves
    Draft --> Cancelled: Admin cancels
    Approved --> [*]: Order complete

    note right of Draft
        Stock not yet deducted.
        Prices not yet set.
        No ledger entries yet.
    end note

    note right of Approved
        Stock deducted from products.
        Customer ledger updated.
        Cash book entry created.
        Receipt available.
    end note
```

#### Detailed Approval Flow

```mermaid
flowchart TD
    StaffLogin([Staff logs in]) --> CreateOrder[POST /sales/create]
    CreateOrder --> ValidateStock{All items\nin stock?}
    ValidateStock --> |No| FlashError[Flash: Insufficient stock]
    FlashError --> CreateOrder
    ValidateStock --> |Yes| SaveDraft[Save Order with status=draft\nNo prices set yet]
    SaveDraft --> AdminReview[Admin reviews order\nGET /sales/orders/id]

    AdminReview --> SetPrices[Admin sets price per item\nin the form]
    SetPrices --> POST[POST /sales/orders/id]
    POST --> ReCheckStock{Re-check stock\nwith row lock}
    ReCheckStock --> |Insufficient| Rollback[DB Rollback\nFlash error]
    ReCheckStock --> |OK| CalcTotals[Calculate total_amount\n& total_profit]
    CalcTotals --> DeductStock[Deduct stock\nCreate StockMovement records]
    DeductStock --> UpdateLedger{Is credit sale\nwith customer?}
    UpdateLedger --> |Yes| CustomerLedger[Create CustomerTransaction\ntype=receivable]
    UpdateLedger --> |No| CashBook
    CustomerLedger --> CheckAdvance{amount_paid > 0?}
    CheckAdvance --> |Yes| PaymentTx[Create CustomerTransaction\ntype=payment]
    CheckAdvance --> |No| CashBook
    PaymentTx --> CashBook[Create CashTransaction\ntype=in]
    CashBook --> MarkApproved[Order status = approved]
    MarkApproved --> Receipt[Redirect to Receipt page]
```

---

### 6.3 Purchase Order Lifecycle

```mermaid
flowchart TD
    Admin([Admin]) --> CreatePO[POST /purchases/create\nSelect distributor + items]
    CreatePO --> SavePO[Save PurchaseOrder\nstatus=pending]
    SavePO --> Review[Review PO Detail page]

    Review --> Receive[POST /purchases/id/receive\nMark as received]
    Receive --> ForEachItem{For each item}
    ForEachItem --> LoadProduct[Load product with row lock]
    LoadProduct --> CalcWAC["Calculate Weighted Average Cost\nWAC = (old_qty×old_cost + new_qty×new_cost)\n/ total_qty"]
    CalcWAC --> UpdateProduct[Update product:\n- stock_quantity += qty\n- cost_price = WAC]
    UpdateProduct --> StockLog[Create StockMovement\nreference_type=purchase_receipt]
    StockLog --> ForEachItem
    ForEachItem --> |Done| CreatePayable[Create SupplierTransaction\ntype=payable]
    CreatePayable --> StatusReceived[PO status = received]

    Review --> RecordPayment[POST /purchases/id/payment\nRecord payment to supplier]
    RecordPayment --> SupplierTx[Create SupplierTransaction\ntype=payment]
    SupplierTx --> CashTx[Create CashTransaction\ntype=out]
    CashTx --> UpdateAmountPaid[Update PO amount_paid\nUpdate payment_status]
```

---

### 6.4 Inventory & Restocking

```mermaid
flowchart TD
    Admin([Admin]) --> ProductList[/products/ — View Catalog]
    ProductList --> ProductDetail[/products/id — Product Detail]

    ProductDetail --> EditBtn[Edit Product Details]
    ProductDetail --> RestockBtn[Quick Restock]
    ProductDetail --> DeleteBtn[Delete Product]

    RestockBtn --> RestockForm[/products/id/restock\nEnter qty, new cost, selling price, payment]
    RestockForm --> HasDist{Product has\ndistributor?}

    HasDist --> |Yes| CreatePO[Create PurchaseOrder\nstatus=received]
    CreatePO --> CreatePOItem[Create PurchaseOrderItem]
    CreatePOItem --> SupplierTx[Create SupplierTransaction\ntype=payable]
    SupplierTx --> PaidCheck{amount_paid > 0?}
    PaidCheck --> |Yes| PaymentTx[Create SupplierTransaction\ntype=payment + CashTransaction out]
    PaidCheck --> |No| CalcWAC2
    PaymentTx --> CalcWAC2

    HasDist --> |No| CalcWAC2["Calculate new WAC\ncost_price = (old_val + new_val) / total_qty"]
    CalcWAC2 --> UpdateStock[Update product.stock_quantity\nUpdate product.cost_price\nUpdate product.selling_price]
    UpdateStock --> StockMove[Create StockMovement\nreference_type=restock]
    StockMove --> Done([Redirect to Product Detail])
```

---

### 6.5 Customer Account & Payments

```mermaid
flowchart TD
    Admin([Admin]) --> CustomerList[/customers/ — View all customers]
    CustomerList --> CustomerDetail[/customers/id — Customer Detail]

    CustomerDetail --> OrdersTab[Orders Tab\nAll orders with amounts due]
    CustomerDetail --> LedgerTab[Account Ledger Tab\nAll debit/credit transactions]
    CustomerDetail --> PaymentForm[Record Account Payment]

    PaymentForm --> SubmitPayment[POST /customers/id/payment]
    SubmitPayment --> ValidateAmt{Amount > 0?}
    ValidateAmt --> |No| Error[Return error]
    ValidateAmt --> |Yes| CreateTx[Create CustomerTransaction\ntype=payment]
    CreateTx --> CreateCash[Create CashTransaction\ntype=in]
    CreateCash --> FIFO["FIFO Allocation:\nSort unpaid orders by created_at ASC\nAllocate payment to oldest orders first"]
    FIFO --> Done([Payment applied])
```

#### FIFO Payment Allocation Example

```
Customer owes:   Order #1 → Rs. 3,000   Order #2 → Rs. 5,000
Payment received: Rs. 4,000

Allocation:
  → Order #1: fully paid (Rs. 3,000)
  → Order #2: partially paid (Rs. 1,000 applied, Rs. 4,000 still due)
```

---

### 6.6 Expense Tracking

```mermaid
flowchart LR
    Admin([Admin]) --> AddExpense[POST /expenses/add\ncategory + amount]
    AddExpense --> SaveExpense[Save Expense record]
    SaveExpense --> CashOut[Create CashTransaction\ntype=out, source=expense]
    CashOut --> EditCheck{Admin edits\nexpense?}
    EditCheck --> |Amount changed| AdjTx[Create CashTransaction\nadjustment in/out for the difference]
    EditCheck --> |No change| End([Done])
    AdjTx --> End

    style Admin fill:#3b82f6,color:white
```

> **Note:** Expenses cannot be hard-deleted. If an expense was entered incorrectly, the admin edits the amount and an automatic cash book adjustment is recorded to keep the ledger accurate.

---

### 6.7 Cash Book & Ledgers

The system maintains **three interlinked ledgers**:

```mermaid
graph LR
    subgraph "Customer Ledger (Accounts Receivable)"
        CR1["receivable: Rs.+\n(when order approved)"]
        CR2["payment: Rs.−\n(when customer pays)"]
    end

    subgraph "Supplier Ledger (Accounts Payable)"
        SR1["payable: Rs.+\n(when PO received / restocked)"]
        SR2["payment: Rs.−\n(when we pay supplier)"]
    end

    subgraph "Cash Book"
        CB1["IN: sales, customer_payment"]
        CB2["OUT: supplier_payment, expense"]
    end

    SaleApproved([Sale Approved]) --> CR1
    SaleApproved --> CB1
    CustomerPays([Customer Pays]) --> CR2
    CustomerPays --> CB1

    POReceived([Purchase Order Received]) --> SR1
    WePaySupplier([We Pay Supplier]) --> SR2
    WePaySupplier --> CB2

    ExpenseAdded([Expense Added]) --> CB2
```

#### Running Balance Calculation

The Cash Book computes a running balance by iterating transactions in chronological order:

```
Balance = 0
For each transaction (oldest first):
    if type == 'in':  balance += amount
    if type == 'out': balance -= amount
    record running_balance = current balance

Return list in reverse (latest first) for display
```

---

### 6.8 Analytics & Reports

```mermaid
graph TD
    Admin([Admin]) --> AnalyticsDash[/analytics/ — Analytics Dashboard]

    AnalyticsDash --> Filter[Filter by Year + Month]
    Filter --> Metrics

    subgraph Metrics["Dashboard Metrics"]
        M1[Total Revenue\nsum of approved order amounts]
        M2[Gross Profit\nsum of order profits]
        M3[Total Expenses\nsum of expense amounts]
        M4[Net Profit = Gross Profit − Expenses]
        M5[Total Purchases\nsum of received PO amounts]
        M6[Total Receivables\namounts customers owe us]
        M7[Total Payables\namounts we owe suppliers]
    end

    subgraph Charts["Visual Charts"]
        CH1[Monthly Sales Line Chart\nCharts.js]
        CH2[Revenue Allocation Pie\nCOGS vs Expenses vs Profit]
    end

    subgraph Tables["Data Tables"]
        T1[Top 10 Selling Products\nby quantity + revenue + profit]
        T2[Top 5 Distributors\nby purchase volume]
    end

    AnalyticsDash --> Receivables[/analytics/receivables\nCustomers who owe money]
    AnalyticsDash --> Payables[/analytics/payables\nSuppliers we owe]
    AnalyticsDash --> CashBook[/analytics/cashbook\nFull cash ledger with filters]
    AnalyticsDash --> StockMov[/analytics/stock-movements\nAll inventory change logs]
```

---

## 7. Data Flow Between Modules

This diagram shows how a single business transaction creates records across multiple modules simultaneously:

```mermaid
flowchart TD
    ApproveOrder(["Admin Approves Order"]) --> |for each item| DeductStock["Product.stock_quantity -= qty"]
    DeductStock --> StockMove["StockMovement\nreference_type='sale'"]

    ApproveOrder --> CalcTotal["Order.total_amount\nOrder.total_profit"]

    ApproveOrder --> |if has customer| CustReceivable["CustomerTransaction\ntype='receivable'\namount=total"]
    CustReceivable --> |if advance paid| CustPayment["CustomerTransaction\ntype='payment'\namount=advance"]

    ApproveOrder --> |if amount_paid > 0| CashIn["CashTransaction\ntype='in'\nsource='sales'"]

    style ApproveOrder fill:#10b981,color:white
    style DeductStock fill:#f59e0b,color:white
    style CashIn fill:#3b82f6,color:white
```

```mermaid
flowchart TD
    ReceivePO(["Admin Receives Purchase Order"]) --> |for each item| UpdateStock["Product.stock_quantity += qty\nProduct.cost_price = WAC"]
    UpdateStock --> StockMove["StockMovement\nreference_type='purchase_receipt'"]

    ReceivePO --> Payable["SupplierTransaction\ntype='payable'\namount=total_cost"]

    PaySupplier(["Admin Records Payment to Supplier"]) --> SupplyPay["SupplierTransaction\ntype='payment'"]
    SupplyPay --> CashOut["CashTransaction\ntype='out'\nsource='supplier_payment'"]
    SupplyPay --> UpdatePOPaid["PurchaseOrder.amount_paid += amount\nUpdate payment_status"]

    style ReceivePO fill:#10b981,color:white
    style PaySupplier fill:#ef4444,color:white
```

---

## 8. Code Architecture

### Request Lifecycle

```mermaid
sequenceDiagram
    participant Browser
    participant Blueprint as Blueprint (Route)
    participant Decorator as @login_required / @role_required
    participant Controller
    participant Model
    participant DB

    Browser->>Blueprint: HTTP Request
    Blueprint->>Decorator: Check authentication
    alt Not logged in
        Decorator-->>Browser: Redirect to /login
    end
    Decorator->>Decorator: Check role (if @role_required)
    alt Wrong role
        Decorator-->>Browser: 403 Forbidden
    end
    Blueprint->>Controller: Call static method
    Controller->>Model: Query / mutate data
    Model->>DB: SQL via SQLAlchemy
    DB-->>Model: Result
    Model-->>Controller: Object(s)
    Controller-->>Blueprint: Return data / tuple
    Blueprint->>Blueprint: flash() messages
    Blueprint-->>Browser: render_template() or redirect()
```

### Blueprint URL Structure

| Blueprint | Prefix | Example Routes |
|-----------|--------|----------------|
| `auth` | *(none)* | `/login`, `/logout` |
| `main` | *(none)* | `/` |
| `products` | `/products` | `/products/`, `/products/<id>`, `/products/admin` |
| `sales` | `/sales` | `/sales/create`, `/sales/orders/<id>` |
| `purchases` | `/purchases` | `/purchases/`, `/purchases/create`, `/purchases/<id>` |
| `customers` | `/customers` | `/customers/`, `/customers/<id>` |
| `distributors` | `/distributors` | `/distributors/`, `/distributors/<id>` |
| `expenses` | `/expenses` | `/expenses/`, `/expenses/add` |
| `analytics` | `/analytics` | `/analytics/`, `/analytics/cashbook`, `/analytics/receivables` |

### Controller Return Conventions

Controllers return **tuples** to routes for consistent error handling:

```python
# 2-tuple: (success: bool, message: str)
return True, "Product created successfully!"
return False, "Product not found."

# 3-tuple: (success, message, object)
return True, "Purchase order created!", purchase_order
return False, "Distributor required.", None

# 5-tuple for product details (uses *error unpacking)
return True, product, recent_sales, recent_purchases   # success
return False, None, None, None, "Product not found."   # failure
```

---

*Documentation generated for Suzuki Auto POS — February 2026*
