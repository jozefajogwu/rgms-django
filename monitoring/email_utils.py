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
            template = 'emails/welcome_email.html'
            subject = 'Welcome to RHMS - Doctor Registration'
        elif role.lower() == 'patient':
            template = 'emails/welcome_email.html'
            subject = 'Welcome to RHMS - Patient Registration'
        elif role.lower() == 'caregiver':
            template = 'emails/welcome_email.html'
            subject = 'Welcome to RHMS - Caregiver Registration'
        else:
            template = 'emails/welcome_email.html'
            subject = 'Welcome to RHMS'
        
        # Prepare context
        context = {
            'user_name': user.get_full_name() or user.username,
            'username': user.username,
            'email': user.email,
            'password': password,
            'role': role.capitalize(),
            'login_url': getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000') + '/login/',
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


def send_vital_alert_email(patient, reading, alerts, doctor_emails, doctor_name=None):
    """
    Send vital alert email to doctors
    """
    if not doctor_emails:
        logger.warning("No doctor emails provided for vital alert")
        return False
    
    try:
        # Prepare context
        context = {
            'patient': patient,
            'reading': reading,
            'alerts': alerts,
            'doctor_name': doctor_name or 'the care team',
            'patient_url': getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000') + f'/patient/{patient.id}/',
        }
        
        # Render email
        html_message = render_to_string('emails/new_vitals_alert.html', context)
        plain_message = strip_tags(html_message)
        
        # Send email
        send_mail(
            f'📊 New Vitals Recorded - {patient.full_name}',
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            doctor_emails if isinstance(doctor_emails, list) else [doctor_emails],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"✅ Vital alert email sent for {patient.full_name}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Vital alert email failed: {str(e)}")
        return False


def send_alert_notification_email(patient, alert, doctor_emails, doctor_name=None):
    """
    Send alert notification email to doctors
    """
    if not doctor_emails:
        logger.warning("No doctor emails provided for alert notification")
        return False
    
    try:
        context = {
            'patient': patient,
            'alert': alert,
            'doctor_name': doctor_name or 'the care team',
            'patient_url': getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000') + f'/patient/{patient.id}/',
            'alert_url': getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000') + f'/alert/{alert.id}/',
        }
        
        html_message = render_to_string('emails/alert_notification.html', context)
        plain_message = strip_tags(html_message)
        
        subject = f"🚨 CRITICAL Alert - {patient.full_name}" if alert.severity == 'critical' else f"⚠️ Alert - {patient.full_name}"
        
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            doctor_emails if isinstance(doctor_emails, list) else [doctor_emails],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"✅ Alert notification email sent for {patient.full_name}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Alert notification email failed: {str(e)}")
        return False