from django.contrib import admin
from django.urls import path, include
from monitoring import views
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    

    # Public landing page
    path('', views.landing_page, name='home'),

    # Auth
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Dashboards
    path('doctor/dashboard/', views.doctor_dashboard, name='doctor_dashboard'),
    path('doctor/patients/', views.doctor_patients_list, name='doctor_patients_list'),
    path('doctor/triage/', views.triage_desk, name='triage_desk'),
    path('doctor/live-telemetry/', views.live_telemetry, name='live_telemetry'),
    path('caregiver/dashboard/', views.caregiver_dashboard, name='caregiver_dashboard'),

    # Caregiver actions
    path('caregiver/add-reading/', views.add_vital_reading, name='add_vital_reading'),

    # Alerts
    path('alerts/<int:alert_id>/review/', views.mark_alert_reviewed, name='mark_alert_reviewed'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)