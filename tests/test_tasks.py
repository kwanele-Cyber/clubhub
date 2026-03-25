
import unittest
from datetime import datetime
from core import create_app, db
from modules.auth.models import User
from modules.tasks.models import Task
from core.config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'test-secret-key'

class TaskTestCase(unittest.TestCase):

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

    def tearDown(self):
        """Tear down all initialized variables."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_create_task(self):
        """Test task creation."""
        response = self.client.post('/tasks/create', data=dict(
            title='Test Task',
            description='This is a test task.',
            due_date=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        ), follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Task created successfully!', response.data)
        task = Task.query.filter_by(title='Test Task').first()
        self.assertIsNotNone(task)

    def test_complete_task(self):
        """Test marking a task as complete."""
        task = Task(title='Incomplete Task', description='This task needs to be completed.', user_id=self.user.id)
        db.session.add(task)
        db.session.commit()

        response = self.client.post(f'/tasks/complete/{task.id}', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Task marked as complete!', response.data)
        completed_task = Task.query.get(task.id)
        self.assertTrue(completed_task.is_completed)

    def test_unauthorized_task_access(self):
        """Test that unauthorized users cannot create tasks."""
        # Log out the user
        self.client.get('/logout', follow_redirects=True)

        response = self.client.get('/tasks/create', follow_redirects=True)
        self.assertIn(b'Please log in to access this page.', response.data)

if __name__ == '__main__':
    unittest.main()
