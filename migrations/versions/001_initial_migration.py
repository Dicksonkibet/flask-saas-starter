# migration_fix.py - Run this to fix your database schema
from app import app, db
from app.models.user import User, UserRole
from app.models.organization import Organization, SubscriptionStatus

def fix_database_schema():
    """Fix the database schema and relationships"""
    with app.app_context():
        try:
            print("Creating database tables...")
            
            # Drop and recreate tables if needed (WARNING: This will delete existing data)
            # Only do this in development!
            # db.drop_all()
            
            # Create all tables
            db.create_all()
            
            # Check if tables exist and have correct structure
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            print(f"Tables found: {tables}")
            
            if 'users' in tables:
                users_columns = [col['name'] for col in inspector.get_columns('users')]
                print(f"Users columns: {users_columns}")
            
            if 'organizations' in tables:
                orgs_columns = [col['name'] for col in inspector.get_columns('organizations')]
                print(f"Organizations columns: {orgs_columns}")
            
            # Test creating an organization and user
            print("\nTesting registration flow...")
            
            # Check if test user already exists
            existing_user = User.query.filter_by(email='test@example.com').first()
            if existing_user:
                print("Test user already exists, skipping test creation")
                return
            
            # Create test organization
            test_org = Organization(
                name="Test Organization",
                slug="test-org",
                subscription_plan='free',
                subscription_status=SubscriptionStatus.TRIAL
            )
            db.session.add(test_org)
            db.session.flush()
            
            print(f"Created test organization with ID: {test_org.id}")
            
            # Create test user
            test_user = User(
                username='testuser',
                email='test@example.com',
                first_name='Test',
                last_name='User',
                role=UserRole.ADMIN,
                organization_id=test_org.id,
                is_active=True,
                is_verified=True
            )
            test_user.set_password('testpassword')
            
            db.session.add(test_user)
            db.session.flush()
            
            # Set organization owner
            test_org.owner_id = test_user.id
            
            db.session.commit()
            
            print(f"Created test user with ID: {test_user.id}")
            print("Test registration successful!")
            
            # Clean up test data
            db.session.delete(test_user)
            db.session.delete(test_org)
            db.session.commit()
            
            print("Cleaned up test data. Database is ready!")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error fixing database: {e}")
            import traceback
            print(traceback.format_exc())

if __name__ == '__main__':
    fix_database_schema()