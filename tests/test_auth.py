
import unittest
from app import create_app, db
from app.models.user import User, UserRole
from app.models.organization import Organization

class AuthTestCase(unittest.TestCase):
    """Test authentication functionality"""
    
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()
        
        # Create test organization
        self.test_org = Organization(name='Test Org', slug='test-org')
        db.session.add(self.test_org)
        db.session.commit()
        
        # Create test user
        self.test_user = User(
            username='testuser',
            email='test@example.com',
            first_name='Test',
            last_name='User',
            organization_id=self.test_org.id,
            is_verified=True
        )
        self.test_user.set_password('testpass123')
        db.session.add(self.test_user)
        db.session.commit()
    
    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_user_registration(self):
        """Test user registration"""
        response = self.client.post('/auth/register', data={
            'first_name': 'John',
            'last_name': 'Doe',
            'username': 'johndoe',
            'email': 'john@example.com',
            'password': 'password123',
            'password2': 'password123'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        user = User.query.filter_by(email='john@example.com').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.username, 'johndoe')
    
    def test_user_login(self):
        """Test user login"""
        response = self.client.post('/auth/login', data={
            'email': 'test@example.com',
            'password': 'testpass123'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Dashboard', response.data)
    
    def test_invalid_login(self):
        """Test login with invalid credentials"""
        response = self.client.post('/auth/login', data={
            'email': 'test@example.com',
            'password': 'wrongpassword'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Invalid email or password', response.data)
    
    def test_api_authentication(self):
        """Test API authentication"""
        # Get access token
        response = self.client.post('/api/v1/auth/login', 
                                  json={
                                      'email': 'test@example.com',
                                      'password': 'testpass123'
                                  })
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('access_token', data)
        
        # Use token to access protected endpoint
        token = data['access_token']
        response = self.client.get('/api/v1/auth/me',
                                 headers={'Authorization': f'Bearer {token}'})
        
        self.assertEqual(response.status_code, 200)
        user_data = response.get_json()
        self.assertEqual(user_data['user']['email'], 'test@example.com')

if __name__ == '__main__':
    unittest.main()