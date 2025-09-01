# Flask SaaS Starter Template

A comprehensive, production-ready Flask template for building SaaS applications quickly. This template includes everything you need to launch your SaaS: authentication, billing, admin dashboard, API, and more.

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=app

# Run specific test file
python -m pytest tests/test_auth.py
```

## 🚀 Deployment

### Production Deployment

1. **Environment Setup:**
   ```bash
   export FLASK_ENV=production
   export SECRET_KEY=your-production-secret-key
   export DATABASE_URL=your-production-database-url
   ```

2. **Database Migration:**
   ```bash
   flask db upgrade
   ```

3. **Run with Gunicorn:**
   ```bash
   gunicorn --bind 0.0.0.0:8000 --workers 4 run:app
   ```

### Docker Deployment

```bash
# Build and run
docker-compose -f docker-compose.prod.yml up -d

# Or with custom environment
docker build -t flask-saas-starter .
docker run -p 8000:8000 --env-file .env flask-saas-starter
```

### Heroku Deployment

1. Create Heroku app:
   ```bash
   heroku create your-app-name
   ```

2. Add addons:
   ```bash
   heroku addons:create heroku-postgresql:hobby-dev
   heroku addons:create heroku-redis:hobby-dev
   ```

3. Configure environment:
   ```bash
   heroku config:set FLASK_ENV=production
   heroku config:set SECRET_KEY=your-secret-key
   ```

4. Deploy:
   ```bash
   git push heroku main
   heroku run flask db upgrade
   ```

## 🔐 Security Features

- **CSRF Protection** - All forms protected against CSRF attacks
- **SQL Injection Prevention** - SQLAlchemy ORM with parameterized queries
- **Password Security** - Bcrypt hashing with salt
- **Rate Limiting** - API and form submission protection
- **Input Validation** - WTForms validation on all inputs
- **XSS Prevention** - Template escaping enabled
- **Secure Headers** - Security headers for production
- **Audit Logging** - Track all user actions

## 📊 Analytics & Monitoring

### Built-in Analytics
- User registration trends
- Login patterns
- Feature usage statistics
- Subscription metrics

### Monitoring Integration
- Error tracking with Sentry (add SENTRY_DSN)
- Performance monitoring
- Uptime monitoring endpoints

## 🔌 Integrations

### Payment Processing
- **Stripe** - Credit card processing
- **PayPal** - Alternative payment method
- **Bank transfers** - For enterprise clients

### Email Services
- **SendGrid** - Transactional emails
- **Mailgun** - Email delivery
- **Amazon SES** - AWS email service

### Storage
- **AWS S3** - File storage
- **Google Cloud Storage** - Alternative storage
- **Local filesystem** - Development storage

## 🛡️ Best Practices

### Security Checklist
- [ ] Change default secret keys
- [ ] Configure HTTPS in production
- [ ] Set up proper CORS policies
- [ ] Enable rate limiting
- [ ] Configure secure headers
- [ ] Set up monitoring and logging

### Performance Optimization
- [ ] Configure Redis caching
- [ ] Set up CDN for static files
- [ ] Optimize database queries
- [ ] Enable compression
- [ ] Set up database connection pooling

## 🎯 Customization Examples

### Adding a New Feature

1. **Create the model:**
   ```python
   # app/models/project.py
   class Project(db.Model):
       id = db.Column(db.Integer, primary_key=True)
       name = db.Column(db.String(100), nullable=False)
       organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))
   ```

2. **Create the blueprint:**
   ```python
   # app/projects/__init__.py
   from flask import Blueprint
   bp = Blueprint('projects', __name__)
   from app.projects import routes
   ```

3. **Add routes:**
   ```python
   # app/projects/routes.py
   @bp.route('/')
   @login_required
   def index():
       projects = Project.query.filter_by(organization_id=current_user.organization_id).all()
       return render_template('projects/index.html', projects=projects)
   ```

4. **Register blueprint:**
   ```python
   # app/__init__.py
   from app.projects import bp as projects_bp
   app.register_blueprint(projects_bp, url_prefix='/projects')
   ```

### Custom API Endpoints

```python
# app/api/custom.py
@bp.route('/custom-endpoint', methods=['POST'])
@jwt_required()
@limiter.limit("30 per minute")
def custom_endpoint():
    data = request.get_json()
    # Process data
    return jsonify({'success': True, 'data': result})
```

## 📈 Scaling Considerations

### Database Scaling
- Use connection pooling
- Implement read replicas
- Consider database sharding for large applications

### Application Scaling
- Use Gunicorn with multiple workers
- Implement horizontal scaling with load balancers
- Use Celery for background tasks

### Monitoring & Logging
- Set up centralized logging (ELK stack)
- Implement health check endpoints
- Use APM tools for performance monitoring

## 🤝 Contributing

This template is designed to be customized for your specific needs. Common customizations include:

1. **Adding new user roles**
2. **Implementing additional payment providers**
3. **Adding social login options**
4. **Customizing the UI theme**
5. **Adding new API endpoints**

## 📋 License Options for Your Template

When selling this template, consider these licensing options:

### Single License
- One project use
- No redistribution
- 6 months support
- Price: $50-100

### Extended License
- Multiple projects
- Client projects allowed
- 12 months support
- Source code included
- Price: $200-400

### Developer License
- Unlimited projects
- Resale rights (with modifications)
- Lifetime updates
- Priority support
- Price: $500-1000

## 🛠️ Template Customization for Buyers

### Quick Customization Steps

1. **Brand Customization:**
   - Update `app/templates/base.html` with your branding
   - Modify `app/static/css/style.css` for colors and styling
   - Replace logo files in `app/static/img/`

2. **Feature Configuration:**
   - Edit `config.py` for subscription plans
   - Modify `app/models/` for custom data structures
   - Update API endpoints in `app/api/`

3. **Email Templates:**
   - Customize `app/templates/emails/` for your brand
   - Update email content and styling

4. **Database Schema:**
   - Add custom models in `app/models/`
   - Create migrations with `flask db migrate`

### Advanced Customizations

- **Payment Integration:** Full Stripe integration with webhooks
- **Social Login:** Google, GitHub, Facebook login options
- **File Storage:** AWS S3, Google Cloud Storage integration
- **Real-time Features:** WebSocket integration for live updates
- **Mobile API:** React Native or Flutter compatible API
- **Multi-language:** i18n support for internationalization

## 📞 Support & Documentation

### Getting Help
- Check the documentation in `/docs/`
- Review example implementations
- Join our community forum
- Submit issues on GitHub

### Professional Services
- Custom development
- Deployment assistance
- Code review and optimization
- Training and consultation

---

**Ready to build your SaaS?** This template provides everything you need to launch quickly while maintaining production-quality code and security standards.

For questions about this template, contact: support@yourcompany.com
"""

# ============================================================================
# 40. FINAL TEMPLATE STRUCTURE SUMMARY
# ============================================================================

"""
FLASK SAAS STARTER TEMPLATE - COMPLETE PACKAGE

This production-ready Flask SaaS template includes:

✅ AUTHENTICATION SYSTEM
- Multi-role user management (User/Manager/Admin)
- Email verification and password reset
- Two-factor authentication ready
- JWT API authentication
- Session management

✅ ORGANIZATION MANAGEMENT
- Multi-tenant architecture
- Team collaboration features
- Role-based permissions
- Organization settings

✅ SUBSCRIPTION & BILLING
- Stripe integration
- Multiple subscription plans
- Trial period management
- Usage tracking and limits

✅ ADMIN DASHBOARD
- Beautiful, responsive interface
- Real-time analytics and charts
- User and organization management
- System monitoring tools

✅ RESTful API
- JWT authentication
- Rate limiting
- Comprehensive endpoints
- API documentation ready

✅ MODERN FRONTEND
- Bootstrap 5 with custom styling
- HTMX for dynamic updates
- Dark/light theme toggle
- Mobile-responsive design
- Chart.js for analytics

✅ DEVELOPER EXPERIENCE
- Docker configuration
- Testing framework
- CLI management commands
- Database migrations
- Comprehensive documentation

✅ PRODUCTION FEATURES
- Email system with templates
- File upload handling
- Audit logging
- Notification system
- Webhook support
- Error handling
- Security best practices

✅ DEPLOYMENT READY
- Gunicorn configuration
- Docker setup
- Heroku deployment guide
- Environment configuration
- Production security settings

MARKET VALUE: $200-500+
TARGET BUYERS: Developers, startups, agencies
CUSTOMIZATION: Highly flexible and modular
SUPPORT: Complete documentation included

This template saves 2-3 months of development time and provides a solid foundation for any SaaS application.
"""🚀 Features

### Core Features
- **Multi-role Authentication** - User, Manager, Admin roles with permissions
- **Organization Management** - Multi-tenant architecture with team support
- **Subscription Billing** - Stripe integration with multiple plans
- **RESTful API** - JWT authentication with comprehensive endpoints
- **Admin Dashboard** - Beautiful admin interface with analytics
- **Real-time Updates** - HTMX for dynamic content updates
- **Email System** - Transactional emails with templates
- **File Uploads** - Secure file handling with thumbnails
- **Audit Logging** - Track all user actions and changes
- **Notification System** - In-app and email notifications

### Technical Features
- **Modern UI** - Bootstrap 5 with dark/light theme
- **Database Agnostic** - SQLite, PostgreSQL, MySQL support
- **Docker Ready** - Complete Docker configuration
- **Testing Framework** - Comprehensive test suite
- **CLI Commands** - Custom management commands
- **Rate Limiting** - API protection and abuse prevention
- **Caching** - Redis integration for performance
- **Security** - CSRF protection, secure headers, input validation

## 🛠️ Quick Start

### Prerequisites
- Python 3.8+
- Node.js (for asset compilation)
- Redis (for caching and rate limiting)
- PostgreSQL (recommended for production)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/flask-saas-starter.git
   cd flask-saas-starter
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Initialize database:**
   ```bash
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

6. **Create admin user:**
   ```bash
   flask create-admin
   ```

7. **Run the application:**
   ```bash
   flask run
   ```

Visit `http://localhost:5000` to see your application!

### Docker Setup

For a complete development environment with PostgreSQL and Redis:

```bash
docker-compose up -d
```

This will start:
- Flask application on port 5000
- PostgreSQL database on port 5432
- Redis on port 6379
- Celery worker for background tasks

## 📁 Project Structure

```
flask-saas-starter/
├── app/                    # Main application package
│   ├── models/            # Database models
│   ├── auth/              # Authentication blueprint
│   ├── dashboard/         # Dashboard blueprint
│   ├── api/               # API blueprint
│   ├── admin/             # Admin blueprint
│   ├── templates/         # Jinja2 templates
│   ├── static/            # CSS, JS, images
│   ├── utils/             # Utility functions
│   └── cli/               # CLI commands
├── migrations/            # Database migrations
├── tests/                 # Test suite
├── docker-compose.yml     # Docker configuration
├── requirements.txt       # Python dependencies
└── config.py             # Application configuration
```

## 🔧 Configuration

### Environment Variables

Key environment variables to configure:

- `FLASK_ENV` - Application environment (development/production)
- `SECRET_KEY` - Flask secret key for sessions
- `DATABASE_URL` - Database connection string
- `REDIS_URL` - Redis connection for caching
- `MAIL_*` - Email configuration
- `STRIPE_*` - Stripe keys for billing

### Database Configuration

The template supports multiple databases:

- **SQLite** (default for development)
- **PostgreSQL** (recommended for production)
- **MySQL** (alternative option)

### Subscription Plans

Configure your subscription plans in `config.py`:

```python
SUBSCRIPTION_PLANS = {
    'free': {'name': 'Free', 'price': 0, 'features': ['Basic features']},
    'pro': {'name': 'Pro', 'price': 29, 'features': ['Advanced features']},
    'enterprise': {'name': 'Enterprise', 'price': 99, 'features': ['All features']}
}
```

## 🎨 Customization

### Branding
1. Update logo and colors in `app/static/css/style.css`
2. Modify `app/templates/base.html` for navigation
3. Update email templates in `app/templates/emails/`

### Adding Features
1. Create new blueprint in `app/your_feature/`
2. Add models in `app/models/`
3. Register blueprint in `app/__init__.py`
4. Add routes and templates

### API Extensions
Add new API endpoints in `app/api/` following the existing pattern:

```python
@bp.route('/your-endpoint', methods=['POST'])
@jwt_required()
@limiter.limit("10 per minute")
def your_endpoint():
    # Your code here
    pass
```

## 
            </div>
        {% endif %}
    {% endwith %}
    
    <!-- Main Content -->
    <main>
        {% block content %}{% endblock %}
    </main>
    
    <!-- Footer -->
    <footer class="bg-light border-top mt-5">
        <div class="container py-4">
            <div class="row">
                <div class="col-md-6">
                    <h6>Flask SaaS Starter</h6>
                    <p class="text-muted small">Production-ready Flask template for SaaS applications.</p>
                </div>
                <div class="col-md-6 text-md-end">
                    <a href="{{ url_for('main.about') }}" class="text-decoration-none me-3">About</a>
                    <a href="{{ url_for('main.pricing') }}" class="text-decoration-none me-3">Pricing</a>
                    <a href="#" class="text-decoration-none">Support</a>
                </div>
            </div>
        </div>
    </footer>
    
    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    <!-- HTMX -->
    <script src="https://unpkg.com/htmx.org@1.9.6"></script>
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <!-- Custom JS -->
    <script src="{{ url_for('static', filename='js/app.js') }}"></script>
    
    {% block scripts %}{% endblock %}
</body>
</html>
"""
