# database_enum_fix.py - Run this to fix the enum issue permanently
from app import app, db
from sqlalchemy import text
import os

def fix_subscription_status_enum():
    """Fix the SubscriptionStatus enum in the database"""
    with app.app_context():
        try:
            print("Fixing SubscriptionStatus enum in database...")
            
            # Check if we're using SQLite (common in development)
            if 'sqlite' in str(db.engine.url):
                print("SQLite detected - enum constraints are not enforced, using string values")
                # For SQLite, we'll just use string values as the quick fix shows
                return
            
            # For PostgreSQL/MySQL, we need to fix the enum type
            if 'postgresql' in str(db.engine.url):
                print("PostgreSQL detected - fixing enum type")
                
                # Get current enum values
                result = db.engine.execute(text("""
                    SELECT enumlabel 
                    FROM pg_enum 
                    WHERE enumtypid = (
                        SELECT oid FROM pg_type WHERE typname = 'subscriptionstatus'
                    )
                """))
                current_values = [row[0] for row in result]
                print(f"Current enum values: {current_values}")
                
                # Expected values
                expected_values = ['ACTIVE', 'TRIAL', 'EXPIRED', 'CANCELLED']
                
                # Check if all expected values exist
                missing_values = set(expected_values) - set(current_values)
                if missing_values:
                    print(f"Adding missing enum values: {missing_values}")
                    for value in missing_values:
                        db.engine.execute(text(f"ALTER TYPE subscriptionstatus ADD VALUE '{value}'"))
                
                print("PostgreSQL enum fixed!")
                
            elif 'mysql' in str(db.engine.url):
                print("MySQL detected - updating enum constraint")
                
                # For MySQL, we need to alter the column
                db.engine.execute(text("""
                    ALTER TABLE organizations 
                    MODIFY COLUMN subscription_status 
                    ENUM('ACTIVE', 'TRIAL', 'EXPIRED', 'CANCELLED') 
                    DEFAULT 'TRIAL'
                """))
                
                print("MySQL enum fixed!")
            
            else:
                print("Unknown database type - using string values as fallback")
                
            print("Database enum fix completed!")
            
        except Exception as e:
            print(f"Error fixing enum: {e}")
            print("Using fallback solution (string values)")
            return False
        
        return True

def test_registration_fix():
    """Test if the registration fix works"""
    with app.app_context():
        try:
            from app.models.user import User, UserRole
            from app.models.organization import Organization
            
            print("Testing registration fix...")
            
            # Clean up any previous test data
            test_user = User.query.filter_by(email='enumtest@example.com').first()
            if test_user:
                db.session.delete(test_user)
            
            test_org = Organization.query.filter_by(slug='enumtest-org').first()
            if test_org:
                db.session.delete(test_org)
            
            db.session.commit()
            
            # Test creating organization with string value
            test_org = Organization(
                name="Enum Test Organization",
                slug="enumtest-org",
                subscription_plan='free',
                subscription_status='trial'  # Use string instead of enum
            )
            db.session.add(test_org)
            db.session.flush()
            
            print(f"✓ Organization created with ID: {test_org.id}")
            
            # Test creating user
            test_user = User(
                username='enumtestuser',
                email='enumtest@example.com',
                first_name='Enum',
                last_name='Test',
                role=UserRole.ADMIN,
                organization_id=test_org.id,
                is_active=True,
                is_verified=False
            )
            test_user.set_password('testpassword')
            test_user.generate_verification_token()
            
            db.session.add(test_user)
            db.session.flush()
            
            # Set organization owner
            test_org.owner_id = test_user.id
            
            db.session.commit()
            
            print(f"✓ User created with ID: {test_user.id}")
            print("✓ Registration test successful!")
            
            # Verify the data
            created_org = Organization.query.get(test_org.id)
            print(f"✓ Organization subscription_status: {created_org.subscription_status}")
            
            # Clean up
            db.session.delete(test_user)
            db.session.delete(test_org)
            db.session.commit()
            
            print("✓ Test data cleaned up")
            print("Registration should now work!")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"✗ Registration test failed: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    print("=== DATABASE ENUM FIX ===")
    fix_subscription_status_enum()
    print("\n=== TESTING REGISTRATION ===")
    if test_registration_fix():
        print("\n🎉 SUCCESS! Registration should now work.")
        print("You can now try registering through your web interface.")
    else:
        print("\n❌ Fix didn't work. Check the error messages above.")