
import click
from flask.cli import with_appcontext
from app import db
from app.models.user import User, UserRole
from app.models.organization import Organization

def register_commands(app):
    """Register CLI commands with the app"""
    
    @app.cli.command()
    @with_appcontext
    def init_db():
        """Initialize the database"""
        db.create_all()
        click.echo('Database initialized.')
    
    @app.cli.command()
    @with_appcontext
    def create_admin():
        """Create admin user"""
        email = click.prompt('Admin email')
        password = click.prompt('Admin password', hide_input=True)
        first_name = click.prompt('First name')
        last_name = click.prompt('Last name')
        
        # Create admin organization
        org = Organization(name='Admin Organization', slug='admin-org')
        db.session.add(org)
        db.session.flush()
        
        # Create admin user
        admin = User(
            username='admin',
            email=email.lower(),
            first_name=first_name,
            last_name=last_name,
            role=UserRole.ADMIN,
            organization_id=org.id,
            is_verified=True
        )
        admin.set_password(password)
        
        db.session.add(admin)
        org.owner_id = admin.id
        db.session.commit()
        
        click.echo(f'Admin user created: {email}')
    
    @app.cli.command()
    @with_appcontext
    def seed_data():
        """Seed database with sample data"""
        # Add sample organizations and users
        click.echo('Seeding database with sample data...')
        
        # Create sample organization
        org = Organization(
            name='Demo Company',
            slug='demo-company',
            description='A sample organization for demonstration'
        )
        db.session.add(org)
        db.session.flush()
        
        # Create sample users
        users_data = [
            ('john', 'john@demo.com', 'John', 'Doe', UserRole.ADMIN),
            ('jane', 'jane@demo.com', 'Jane', 'Smith', UserRole.MANAGER),
            ('bob', 'bob@demo.com', 'Bob', 'Johnson', UserRole.USER),
        ]
        
        for username, email, first_name, last_name, role in users_data:
            user = User(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                role=role,
                organization_id=org.id,
                is_verified=True
            )
            user.set_password('password123')
            db.session.add(user)
        
        org.owner_id = User.query.filter_by(username='john').first().id
        db.session.commit()
        
        click.echo('Sample data created successfully!')