from app import create_app, db
from app.models.user import User, UserRole
from app.models.organization import Organization, SubscriptionStatus
import os

app = create_app()


@app.shell_context_processor
def make_shell_context():
    """Add models to shell context for easier debugging"""
    return {
        'db': db,
        'User': User,
        'Organization': Organization,
        'UserRole': UserRole,
        'SubscriptionStatus': SubscriptionStatus
    }


def init_database():
    """Initialize database tables without dropping existing ones"""
    with app.app_context():
        try:
            # Only create missing tables
            db.create_all()
            print("Database tables ensured successfully (no drop).")

            # Create a default admin user only if it doesn't already exist
            if not User.query.filter_by(email="admin@example.com").first():
                create_test_data()

        except Exception as e:
            print(f"Error initializing database: {e}")
            raise


def create_test_data():
    """Create test data for development environment"""
    try:
        # Create a test organization
        org = Organization(
            name="Test Organization",
            slug="test-org",
            subscription_plan='free',
            subscription_status=SubscriptionStatus.ACTIVE
        )
        db.session.add(org)
        db.session.flush()  # Get org ID without committing

        # Create a test admin user
        admin_user = User(
            username="admin",
            email="admin@example.com",
            first_name="Admin",
            last_name="User",
            role=UserRole.ADMIN,
            organization_id=org.id,
            is_active=True,
            is_verified=True
        )
        admin_user.set_password("admin123")
        db.session.add(admin_user)

        # Set organization owner
        org.owner_id = admin_user.id

        db.session.commit()
        print("Created test admin user: admin@example.com / admin123")

    except Exception as e:
        db.session.rollback()
        print(f"Error creating test data: {e}")


if __name__ == '__main__':
    # Initialize database before running the app
    print("Starting Flask application...")
    print("Ensuring database schema...")

    # Ensure schema exists but do not drop data
    init_database()

    print("Starting web server on http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
