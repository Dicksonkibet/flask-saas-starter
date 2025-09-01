from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SelectField, SubmitField
from wtforms.validators import DataRequired, URL, Optional, Length
from app import db
from app.models.organization import Organization
from app.utils.decorators import role_required

class OrganizationSettingsForm(FlaskForm):
    name = StringField('Organization Name', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])
    website = StringField('Website', validators=[Optional(), URL()])
    
    # Webhook settings
    webhook_url = StringField('Webhook URL', validators=[Optional(), URL()])
    webhook_secret = StringField('Webhook Secret', validators=[Optional()])
    
    # Notification settings
    email_notifications = BooleanField('Email Notifications')
    weekly_reports = BooleanField('Weekly Reports')
    
    # Theme settings
    theme = SelectField('Default Theme', choices=[('light', 'Light'), ('dark', 'Dark')])
    
    submit = SubmitField('Save Settings')

@bp.route('/settings', methods=['GET', 'POST'])
@login_required
@role_required('manager')
def organization_settings():
    """Organization settings page"""
    org = current_user.organization
    form = OrganizationSettingsForm(obj=org)
    
    # Populate form with current settings
    if org.settings:
        form.webhook_url.data = org.settings.get('webhook_url', '')
        form.webhook_secret.data = org.settings.get('webhook_secret', '')
        form.email_notifications.data = org.settings.get('email_notifications', True)
        form.weekly_reports.data = org.settings.get('weekly_reports', False)
        form.theme.data = org.settings.get('theme', 'light')
    
    if form.validate_on_submit():
        # Update organization basic info
        org.name = form.name.data
        org.description = form.description.data
        org.website = form.website.data
        
        # Update settings JSON
        if not org.settings:
            org.settings = {}
        
        org.settings.update({
            'webhook_url': form.webhook_url.data,
            'webhook_secret': form.webhook_secret.data,
            'email_notifications': form.email_notifications.data,
            'weekly_reports': form.weekly_reports.data,
            'theme': form.theme.data
        })
        
        db.session.commit()
        flash('Settings updated successfully!', 'success')
        return redirect(url_for('dashboard.organization_settings'))
    
    return render_template('dashboard/settings.html', form=form, organization=org)