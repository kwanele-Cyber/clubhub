
import unittest
from core import create_app, db
from modules.auth.models import User
from modules.clubs.models import Club
from modules.forums.models import ForumPost
from core.config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'test-secret-key'

class ForumTestCase(unittest.TestCase):

    def setUp(self):
        """Set up test variables."""
        self.app = create_app(config_class=TestConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Create and log in a test user
        self.user = User(username='testuser', email='test@example.com', role='admin')
        self.user.set_password('password')
        db.session.add(self.user)
        db.session.commit()
        self.client.post('/login', data=dict(email='test@example.com', password='password'), follow_redirects=True)

        # Create a test club for forum association
        self.club = Club(name='Test Club', description='A club for testing purposes.')
        db.session.add(self.club)
        db.session.commit()

    def tearDown(self):
        """Tear down all initialized variables."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_create_forum_post(self):
        """Test forum post creation."""
        response = self.client.post(f'/clubs/{self.club.id}/forums/create', data=dict(
            title='Test Post',
            content='This is a test forum post.'
        ), follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Post created successfully!', response.data)
        post = ForumPost.query.filter_by(title='Test Post').first()
        self.assertIsNotNone(post)

    def test_unauthorized_forum_post_creation(self):
        """Test that unauthorized users cannot create forum posts."""
        # Log out the user
        self.client.get('/logout', follow_redirects=True)

        response = self.client.get(f'/clubs/{self.club.id}/forums/create', follow_redirects=True)
        self.assertIn(b'Please log in to access this page.', response.data)

if __name__ == '__main__':
    unittest.main()
