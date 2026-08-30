# monitoring/email_utils.py

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def send_registration_email(user, password, role, assigned_doctor=None):
    """
    Send registration email to new user
    """
    try:
        # Determine which template to use
        if role.lower() == 'doctor':
            template = 'emails/new_doctor_registration.html'
            subject = 'Welcome to RHMS - Doctor Registration'
        elif role.lower() == 'patient':
            template = 'emails/new_patient_registration.html'
            subject = 'Welcome to RHMS - Patient Registration'
        else:
            template = 'emails/welcome_email.html'
            subject = 'Welcome to RHMS'
        
        # ✅ Prepare context - using user_name for consistent naming
        context = {
            'user_name': user.get_full_name() or user.username,  # ✅ Consistent
            'username': user.username,
            'email': user.email,
            'password': password,
            'role': role.capitalize(),
            'login_url': 'http://127.0.0.1:8000/login/',
        }
        
        if role.lower() == 'patient' and assigned_doctor:
            context['assigned_doctor'] = assigned_doctor
        
        # Render email
        html_message = render_to_string(template, context)
        plain_message = strip_tags(html_message)
        
        # Send email
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"✅ Registration email sent to {user.email} (Role: {role})")
        return True
        
    except Exception as e:
        logger.error(f"❌ Registration email failed: {str(e)}")
        return False