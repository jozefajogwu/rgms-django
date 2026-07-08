from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

def send_patient_registration_email(patient):
    """
    Send registration email to newly added patient
    """
    if not patient.email:
        return False
    
    subject = f"Welcome to RGMS - {patient.full_name}"
    
    # Prepare context for email template
    context = {
        'patient_name': patient.full_name,
        'patient_id': patient.id,
        'gender': patient.gender,
        'care_type': patient.get_care_type_display(),
        'doctor_name': patient.assigned_doctor.get_full_name() if patient.assigned_doctor else 'Not assigned',
        'caregiver_name': patient.assigned_caregiver.get_full_name() if patient.assigned_caregiver else 'Not assigned',
        'registration_date': patient.created_at.strftime('%B %d, %Y'),
    }
    
    # Render HTML email
    html_message = render_to_string('emails/patient_registration.html', context)
    
    # Send email
    try:
        send_mail(
            subject=subject,
            message='',  # Empty because we're using HTML
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[patient.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False