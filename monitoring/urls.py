# monitoring/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('', views.landing_page, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Doctor URLs
    path('doctor/dashboard/', views.doctor_dashboard, name='doctor_dashboard'),
    path('doctor/patients/', views.doctor_patients_list, name='doctor_patients_list'),
    path('doctor/patient/<int:patient_id>/', views.patient_detail, name='patient_detail'),
    
    # Caregiver URLs
    path('caregiver/dashboard/', views.caregiver_dashboard, name='caregiver_dashboard'),
    
    # Vitals
    path('add-vital/', views.add_vital_reading, name='add_vital_reading'),
    
    # Alerts
    path('alert/<int:alert_id>/review/', views.mark_alert_reviewed, name='mark_alert_reviewed'),
    
    # Triage & Telemetry
    path('triage-desk/', views.triage_desk, name='triage_desk'),
    path('live-telemetry/', views.live_telemetry, name='live_telemetry'),
    
     # Alert Documentation URLs
    path('alert/<int:alert_id>/', views.alert_detail, name='alert_detail'),
    path('alert/<int:alert_id>/action/', views.add_alert_action, name='add_alert_action'),
    path('alert/<int:alert_id>/quick-action/', views.add_quick_action, name='add_quick_action'),
    
    
    
    
    # Patient Clinical Note
    path('patient/<int:patient_id>/note/', views.add_patient_note, name='add_patient_note'),
    
    
    
      # ✅ Patient Feedback View
    path('patient/feedback/', views.patient_feedback, name='patient_feedback'),
]