from models import Employee, EmployeePayment, PKT
from extensions import db
from datetime import datetime
from flask_login import current_user
from sqlalchemy import func, extract

class StaffController:
    @staticmethod
    def get_all_employees():
        return Employee.query.filter_by(is_active=True).order_by(Employee.full_name).all()

    @staticmethod
    def get_employee(employee_id):
        return db.session.get(Employee, employee_id)

    @staticmethod
    def create_employee(data):
        nickname = data.get('nickname', '').strip()
        full_name = data.get('full_name', '').strip()
        if not nickname or not full_name:
            return False, "Nickname and full name are required."

        emp = Employee(
            nickname=nickname,
            full_name=full_name,
            phone=data.get('phone', ''),
            address=data.get('address', ''),
            role=data.get('role', ''),
        )
        db.session.add(emp)
        db.session.commit()
        return True, "Employee added successfully!"

    @staticmethod
    def record_payment(employee_id, data):
        emp = db.session.get(Employee, employee_id)
        if not emp:
            return False, "Employee not found."

        amount = float(data.get('amount', 0))
        if amount <= 0:
            return False, "Amount must be greater than 0."

        payment = EmployeePayment(
            employee_id=employee_id,
            payment_type=data.get('payment_type', 'salary'),
            amount=amount,
            notes=data.get('notes', ''),
            created_by=current_user.id,
        )
        db.session.add(payment)
        db.session.commit()
        return True, f"Payment of Rs. {amount:.2f} recorded."

    @staticmethod
    def get_payment_history(employee_id, payment_type=None, start_date=None, end_date=None):
        query = EmployeePayment.query.filter_by(employee_id=employee_id)
        if payment_type:
            query = query.filter_by(payment_type=payment_type)
        if start_date:
            query = query.filter(EmployeePayment.date >= datetime.strptime(start_date, '%Y-%m-%d'))
        if end_date:
            from datetime import timedelta
            query = query.filter(EmployeePayment.date <= datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1))
        return query.order_by(EmployeePayment.date.desc()).all()

    @staticmethod
    def get_salary_summary():
        """Returns monthly/yearly salary totals and employee count."""
        now = datetime.now(PKT)
        month_total = db.session.query(func.sum(EmployeePayment.amount))\
            .filter(extract('year', EmployeePayment.date) == now.year,
                    extract('month', EmployeePayment.date) == now.month).scalar() or 0
        year_total = db.session.query(func.sum(EmployeePayment.amount))\
            .filter(extract('year', EmployeePayment.date) == now.year).scalar() or 0
        emp_count = Employee.query.filter_by(is_active=True).count()

        # Monthly breakdown for chart
        monthly_data = []
        for m in range(1, 13):
            total = db.session.query(func.sum(EmployeePayment.amount))\
                .filter(extract('year', EmployeePayment.date) == now.year,
                        extract('month', EmployeePayment.date) == m).scalar() or 0
            monthly_data.append(float(total))

        return {
            'month_total': float(month_total),
            'year_total': float(year_total),
            'emp_count': emp_count,
            'monthly_data': monthly_data,
        }
