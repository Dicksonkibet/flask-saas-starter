from app import create_app, db
from app.models.user import User
from app.models.organization import Organization

app = create_app()

@app.shell_context_processor
def make_shell_context():
    """Add models to shell context for easier debugging"""
    return {
        'db': db,
        'User': User,
        'Organization': Organization
    }

def init_database():
    """Initialize database tables"""
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            print("Database tables created successfully!")
            
            # Verify tables were created
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"Created tables: {', '.join(tables)}")
            
        except Exception as e:
            print(f"Error creating database tables: {e}")
            raise

if __name__ == '__main__':
    # Initialize database before running the app
    print("Starting Flask application...")
    print("Initializing database...")
    
    init_database()
    
    print("Starting web server on http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)