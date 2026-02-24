from models import Expense, CashTransaction
from extensions import db
from datetime import datetime
from flask_login import current_user

class ExpensesController:
    @staticmethod
    def get_all_expenses():
        expenses = Expense.query.order_by(Expense.expense_date.desc()).all()
        total_expenses = sum(e.amount for e in expenses)
        return expenses, total_expenses

    @staticmethod
    def add_expense(data, current_user_id):
        category = data.get('category')
        amount = data.get('amount')
        description = data.get('description')
        
        if not category or not amount:
            return False, "Category and amount are required.", category
            
        try:
            amount_val = float(amount)
            if amount_val <= 0:
                raise ValueError
        except ValueError:
             return False, "Please enter a valid amount greater than zero.", category
             
        expense = Expense(
            category=category,
            amount=amount_val,
            description=description,
            created_by=current_user_id
        )
        db.session.add(expense)
        db.session.flush()
        
        # Add to Cash Book
        cash_tx = CashTransaction(
            transaction_type='out',
            amount=amount_val,
            source='expense',
            reference_id=expense.id,
            description=f"Expense: {category}",
            created_by=current_user_id
        )
        db.session.add(cash_tx)
        
        db.session.commit()
        
        return True, f"Expense for {category} added successfully!", category

    @staticmethod
    def get_expense(expense_id):
        return db.session.get(Expense, expense_id)

    @staticmethod
    def edit_expense(expense_id, data):
        expense = db.session.get(Expense, expense_id)
        if not expense:
            return False, "Expense not found"
            
        category = data.get('category')
        amount = data.get('amount')
        
        try:
            amount_val = float(amount)
            if amount_val <= 0:
                raise ValueError
        except ValueError:
             return False, "Please enter a valid amount greater than zero."

        # Update Cash Book difference
        diff = amount_val - float(expense.amount)
        if diff != 0:
            tx_type = 'out' if diff > 0 else 'in'
            adj_amount = abs(diff)
            cash_tx = CashTransaction(
                transaction_type=tx_type,
                amount=adj_amount,
                source='expense',
                reference_id=expense.id,
                description=f"Adjustment for Expense #{expense.id}",
                created_by=current_user.id
            )
            db.session.add(cash_tx)
             
        expense.category = category
        expense.amount = amount_val
        expense.description = data.get('description')
        
        db.session.commit()
        return True, "Expense updated successfully!"

    @staticmethod
    def delete_expense(expense_id):
        return False, "Expenses cannot be hard deleted. Add an adjustment instead."
