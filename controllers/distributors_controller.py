from models import Distributor, Product, PurchaseOrder, SupplierTransaction
from extensions import db
from sqlalchemy.exc import IntegrityError

class DistributorsController:
    @staticmethod
    def get_all_distributors():
        return Distributor.query.all()

    @staticmethod
    def add_distributor(data):
        distributor = Distributor(
            name=data.get('name'),
            contact_person=data.get('contact_person'),
            phone=data.get('phone'),
            email=data.get('email'),
            address=data.get('address'),
            payment_terms=int(data.get('payment_terms', 30))
        )
        db.session.add(distributor)
        db.session.commit()
        return True, "Distributor added successfully!"

    @staticmethod
    def get_distributor_details(distributor_id):
        distributor = db.session.get(Distributor, distributor_id)
        if not distributor:
            return False, "Distributor not found.", None, None, None, None
            
        products = Product.query.filter_by(distributor_id=distributor_id).all()
        purchase_orders = PurchaseOrder.query.filter_by(distributor_id=distributor_id).order_by(PurchaseOrder.created_at.desc()).all()
        transactions = SupplierTransaction.query.filter_by(distributor_id=distributor_id).order_by(SupplierTransaction.created_at.desc()).limit(20).all()
        
        return True, "Success", distributor, products, purchase_orders, transactions

    @staticmethod
    def edit_distributor(distributor_id, data):
        distributor = db.session.get(Distributor, distributor_id)
        if not distributor:
            return False, "Distributor not found."
            
        distributor.name = data.get('name')
        distributor.contact_person = data.get('contact_person')
        distributor.phone = data.get('phone')
        distributor.email = data.get('email')
        distributor.address = data.get('address')
        distributor.payment_terms = int(data.get('payment_terms', 30))
        
        db.session.commit()
        return True, "Distributor updated successfully!"

    @staticmethod
    def delete_distributor(distributor_id):
        distributor = db.session.get(Distributor, distributor_id)
        if not distributor:
            return False, "Distributor not found."
            
        try:
            db.session.delete(distributor)
            db.session.commit()
            return True, "Distributor deleted successfully!"
        except IntegrityError:
            db.session.rollback()
            return False, "Cannot delete distributor. It has associated products, orders, or transactions."
