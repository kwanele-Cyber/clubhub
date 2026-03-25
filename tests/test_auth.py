
import unittest
from core import create_app, db
from modules.auth.models import User
from core.config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'test-secret-key'

class AuthTestCase(unittest.TestCase):

    def setUp(self):
        """Set up test variables."""
        self.app = create_app(config_class=TestConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Create a test user
        self.user = User(username='testuser', email='test@example.com')
        self.user.set_password('password')
        db.session.add(self.user)
        db.session.commit()


    def tearDown(self):
        """Tear down all initialized variables."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_registration_form_displays(self):
        """Test that the registration page displays correctly."""
        response = self.client.get('/auth/register')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Register', response.data)

    def test_user_registration(self):
        """Test user registration."""
        response = self.client.post('/auth/register', data=dict(
            username='newuser',
            email='new@example.com',
            password='newpassword',
            confirm_password='newpassword'
        ), follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'A confirmation email has been sent to your email address.', response.data)
        user = User.query.filter_by(email='new@example.com').first()
        self.assertIsNotNone(user)

    def test_duplicate_email_registration(self):
        """Test registration with a duplicate email."""
        response = self.client.post('/auth/register', data=dict(
            username='anotheruser',
            email='test@example.com',
            password='password',
            confirm_password='password'
        ), follow_redirects=True)
        self.assertIn(b'Email is already in use.', response.data)

    def test_login_logout(self):
        """Test login and logout functionality."""
        # Test login with correct credentials
        response = self.client.post('/auth/login', data=dict(
            email='test@example.com',
            password='password'
        ), follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Login successful!', response.data)

        # Test logout
        response = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'You have been logged out.', response.data)

    def test_login_with_wrong_password(self):
        """Test login with incorrect password."""
        response = self.client.post('/auth/login', data=dict(
            email='test@example.com',
            password='wrongpassword'
        ), follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Invalid email or password.', response.data)

if __name__ == '__main__':
    unittest.main()
