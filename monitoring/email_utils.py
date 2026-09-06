from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.urls import reverse  # ✅ ADD THIS LINE
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


def send_vital_alert_email(patient, reading, alerts, doctor_emails, admin_emails=None, doctor_name=None):
    """
    Send vital alert email to doctors and admins when new vitals are recorded
    """
    # Combine doctor emails and admin emails
    all_recipients = []
    
    # Add doctor emails
    if doctor_emails:
        if isinstance(doctor_emails, str):
            all_recipients.append(doctor_emails)
        else:
            all_recipients.extend(doctor_emails)
    
    # Add admin emails
    if admin_emails:
        if isinstance(admin_emails, str):
            all_recipients.append(admin_emails)
        else:
            all_recipients.extend(admin_emails)
    
    # Remove duplicates
    all_recipients = list(set(all_recipients))
    
    if not all_recipients:
        logger.warning("No recipients provided for vital alert email")
        return False
    
    try:
        # Build alert messages
        alert_messages = []
        for alert in alerts:
            alert_messages.append({
                'title': alert.title,
                'message': alert.message,
                'severity': alert.severity
            })
        
        site_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
        
        # Prepare context
        context = {
            'patient': patient,
            'reading': reading,
            'alerts': alert_messages,
            'has_alerts': bool(alert_messages),
            'alert_count': len(alert_messages),
            'patient_url': f"{site_url}{reverse('patient_detail', args=[patient.id])}",
            'doctor_name': doctor_name or 'the care team',
            'reading_time': reading.created_at,
            'is_urgent': any(a['severity'] == 'critical' for a in alert_messages),
        }
        
        # Add vital signs to context
        if reading.systolic_bp:
            context['systolic_bp'] = reading.systolic_bp
            context['diastolic_bp'] = reading.diastolic_bp
        
        if reading.pulse_rate:
            context['pulse_rate'] = reading.pulse_rate
        
        if reading.oxygen_saturation:
            context['oxygen_saturation'] = reading.oxygen_saturation
        
        if reading.fasting_blood_sugar:
            context['fasting_blood_sugar'] = reading.fasting_blood_sugar
        
        if reading.random_blood_sugar:
            context['random_blood_sugar'] = reading.random_blood_sugar
        
        # Determine subject based on alerts
        if alert_messages:
            critical_count = sum(1 for a in alert_messages if a['severity'] == 'critical')
            warning_count = sum(1 for a in alert_messages if a['severity'] == 'warning')
            
            if critical_count > 0:
                subject = f"🚨 CRITICAL ALERT - {patient.full_name} has abnormal vitals!"
            elif warning_count > 0:
                subject = f"⚠️ Alert - {patient.full_name} needs attention"
            else:
                subject = f"📊 New Vitals Recorded - {patient.full_name}"
        else:
            subject = f"📊 New Vitals Recorded - {patient.full_name}"
        
        # Render email
        html_message = render_to_string('emails/new_vitals_alert.html', context)
        plain_message = strip_tags(html_message)
        
        # Send to all recipients
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            all_recipients,
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"✅ Vital alert email sent to {len(all_recipients)} recipients for {patient.full_name}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Vital alert email failed: {str(e)}")
        return False


def send_alert_notification_email(patient, alert, doctor_emails, admin_emails=None, doctor_name=None):
    """
    Send alert notification email to doctors and admins
    """
    # Combine recipients
    all_recipients = []
    
    if doctor_emails:
        if isinstance(doctor_emails, str):
            all_recipients.append(doctor_emails)
        else:
            all_recipients.extend(doctor_emails)
    
    if admin_emails:
        if isinstance(admin_emails, str):
            all_recipients.append(admin_emails)
        else:
            all_recipients.extend(admin_emails)
    
    all_recipients = list(set(all_recipients))
    
    if not all_recipients:
        logger.warning("No recipients provided for alert notification")
        return False
    
    try:
        site_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
        
        context = {
            'patient': patient,
            'alert': alert,
            'alert_severity': alert.get_severity_display(),
            'alert_status': alert.get_status_display(),
            'alert_title': alert.title,
            'alert_message': alert.message,
            'patient_url': f"{site_url}{reverse('patient_detail', args=[patient.id])}",
            'alert_url': f"{site_url}{reverse('alert_detail', args=[alert.id])}",
            'doctor_name': doctor_name or 'the care team',
            'created_at': alert.created_at,
        }
        
        html_message = render_to_string('emails/alert_notification.html', context)
        plain_message = strip_tags(html_message)
        
        subject = f"🚨 CRITICAL Alert - {patient.full_name}" if alert.severity == 'critical' else f"⚠️ Alert - {patient.full_name}"
        
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            all_recipients,
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"✅ Alert notification email sent for {patient.full_name}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Alert notification email failed: {str(e)}")
        return False