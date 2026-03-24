#!/usr/bin/env python
from core import create_app, db
from modules.auth.models import User
from modules.clubs.models import Club
from modules.events.models import Event

def init_db():
    app = create_app()
    with app.app_context():
        db.create_all()
        print("✓ Database tables created")
        
        # Create admin user if not exists
        # if not User.query.filter_by(username='admin').first():
        #     admin = User(username='admin', email='admin@clubhub.com')
        #     admin.set_password('admin123')
        #     db.session.add(admin)
        #     db.session.commit()
        #     print("✓ Admin user created (username: admin, password: admin123)")
        
        print("\n✓ Database initialization complete!")

if __name__ == '__main__':
    init_db()