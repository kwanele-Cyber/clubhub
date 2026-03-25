
import unittest
from core import create_app, db
from modules.auth.models import User
from modules.clubs.models import Club
from core.config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'test-secret-key'

class ClubTestCase(unittest.TestCase):

    def setUp(self):
        """Set up test variables.""" 
        self.app = create_app(config_class=TestConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Create a test user
        self.user = User(username='testuser', email='test@example.com', role='admin')
        self.user.set_password('password')
        db.session.add(self.user)
        db.session.commit()

        # Log in the user
        self.client.post('/login', data=dict(
            email='test@example.com',
            password='password'
        ), follow_redirects=True)

    def tearDown(self):
        """Tear down all initialized variables."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_create_club(self):
        """Test club creation."""
        response = self.client.post('/admin/clubs/create', data=dict(
            name='Test Club',
            description='A club for testing purposes.'
        ), follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Club created successfully!', response.data)
        club = Club.query.filter_by(name='Test Club').first()
        self.assertIsNotNone(club)

    def test_delete_club(self):
        """Test club deletion."""
        club = Club(name='Club to Delete', description='This club will be deleted.')
        db.session.add(club)
        db.session.commit()

        response = self.client.post(f'/admin/clubs/delete/{club.id}', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Club deleted successfully!', response.data)
        deleted_club = Club.query.get(club.id)
        self.assertIsNone(deleted_club)

    def test_edit_club(self):
        """Test editing a club."""
        club = Club(name='Editable Club', description='This is a club that can be edited.')
        db.session.add(club)
        db.session.commit()

        response = self.client.post(f'/admin/clubs/edit/{club.id}', data=dict(
            name='Edited Club Name',
            description='The description has been updated.'
        ), follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Club updated successfully!', response.data)
        
        edited_club = Club.query.get(club.id)
        self.assertEqual(edited_club.name, 'Edited Club Name')
        self.assertEqual(edited_club.description, 'The description has been updated.')

    def test_unauthorized_access(self):
        """Test access to club management without authentication."""
        # Log out the user
        self.client.get('/logout', follow_redirects=True)

        response = self.client.get('/admin/clubs/create', follow_redirects=True)
        self.assertIn(b'Please log in to access this page.', response.data)

if __name__ == '__main__':
    unittest.main()
