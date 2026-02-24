from flask import Flask
from werkzeug.security import generate_password_hash
from extensions import db, login_manager
from routes import register_blueprints
from models import User, Distributor, Product

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = 'secret-key-change-in-production'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pos.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize Extensions
    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register Blueprints
    register_blueprints(app)

    return app

app = create_app()

def initialize_database():
    with app.app_context():
        db.create_all()
        
        # Create users if they don't exist
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin', 
                password_hash=generate_password_hash('admin123'), 
                role='admin',
                full_name='Administrator',
                phone='03001234567'
            )
            staff = User(
                username='staff', 
                password_hash=generate_password_hash('staff123'), 
                role='staff',
                full_name='Staff User',
                phone='03007654321'
            )
            db.session.add_all([admin, staff])        
        db.session.commit()

if __name__ == '__main__':
    initialize_database()
    app.run(debug=True)