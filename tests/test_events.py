
import unittest
from datetime import datetime
from core import create_app, db
from modules.auth.models import User
from modules.clubs.models import Club
from modules.events.models import Event
from core.config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'test-secret-key'

class EventTestCase(unittest.TestCase):

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

        # Create a test club for event association
        self.club = Club(name='Test Club', description='A club for testing purposes.')
        db.session.add(self.club)
        db.session.commit()

    def tearDown(self):
        """Tear down all initialized variables."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_create_event(self):
        """Test event creation."""
        response = self.client.post('/events/create', data=dict(
            title='Test Event',
            description='An event for testing purposes.',
            date=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
            location='Test Location',
            club_id=self.club.id
        ), follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Event created successfully!', response.data)
        event = Event.query.filter_by(title='Test Event').first()
        self.assertIsNotNone(event)

    def test_delete_event(self):
        """Test event deletion."""
        event = Event(title='Event to Delete', description='This event will be deleted.', date=datetime.utcnow(), location='Deletion Location', club_id=self.club.id)
        db.session.add(event)
        db.session.commit()

        response = self.client.post(f'/events/delete/{event.id}', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Event deleted successfully!', response.data)
        deleted_event = Event.query.get(event.id)
        self.assertIsNone(deleted_event)

    def test_edit_event(self):
        """Test editing an event."""
        event = Event(title='Editable Event', description='This event can be edited.', date=datetime.utcnow(), location='Edit Location', club_id=self.club.id)
        db.session.add(event)
        db.session.commit()

        response = self.client.post(f'/events/edit/{event.id}', data=dict(
            title='Edited Event Name',
            description='The description has been updated.',
            date=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
            location='Updated Location',
            club_id=self.club.id
        ), follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Event updated successfully!', response.data)
        
        edited_event = Event.query.get(event.id)
        self.assertEqual(edited_event.title, 'Edited Event Name')
        self.assertEqual(edited_event.description, 'The description has been updated.')

    def test_unauthorized_event_access(self):
        """Test access to event management without authentication."""
        # Log out the user
        self.client.get('/logout', follow_redirects=True)

        response = self.client.get('/events/create', follow_redirects=True)
        self.assertIn(b'Please log in to access this page.', response.data)

if __name__ == '__main__':
    unittest.main()
