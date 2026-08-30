# monitoring/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from .models import VitalReading, DoctorNotification
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=VitalReading)
def notify_doctor_on_vital_submission(sender, instance, created, **kwargs):
    """Send email notification to doctor when vitals are submitted"""
    if not created:
        return
    
    try:
        patient = instance.patient
        doctor = patient.assigned_doctor
        
        if not doctor:
            return
        
        doctor_user = doctor.user
        
        # Skip if doctor has no email
        if not doctor_user.email:
            logger.warning(f"⚠️ Doctor {doctor_user.username} has no email")
            return
        
        # Create in-app notification
        DoctorNotification.objects.create(
            doctor=doctor_user,
            patient=patient,
            reading=instance,
            title='New Vital Reading',
            message=f"🟢 New vitals submitted by {patient.full_name}"
        )
        
        # Prepare reading data
        reading_data = {
            'systolic': instance.systolic_bp,
            'diastolic': instance.diastolic_bp,
            'pulse': instance.pulse_rate,
            'spo2': instance.oxygen_saturation,
            'glucose': instance.fasting_blood_sugar,
            'created_at': instance.created_at.strftime('%Y-%m-%d %H:%M'),
            'is_abnormal': instance.is_abnormal() if hasattr(instance, 'is_abnormal') else False
        }
        
        # Send email
        subject = f'🔔 RGMS Alert: New Vital Reading from {patient.full_name}'
        
        context = {
            'patient_name': patient.full_name,
            'reading': reading_data,
            'doctor_name': doctor_user.get_full_name() or doctor_user.username,
            'dashboard_url': 'http://127.0.0.1:8000/doctor/dashboard/'
        }
        
        html_message = render_to_string('emails/vital_alert.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [doctor_user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"✅ Email sent to {doctor_user.email}")
        
    except Exception as e:
        logger.error(f"❌ Notification error: {str(e)}")