from django.contrib import admin
from django.urls import path
from monitoring import views



urlpatterns = [
    path('admin/', admin.site.urls),

    # Public landing page
    path('', views.landing_page, name='home'),

    # Auth
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Dashboards
    path('doctor/dashboard/', views.doctor_dashboard, name='doctor_dashboard'),
    path('caregiver/dashboard/', views.caregiver_dashboard, name='caregiver_dashboard'),

    # Caregiver actions
    path('caregiver/add-reading/', views.add_vital_reading, name='add_vital_reading'),

    # Alerts
    path('alerts/<int:alert_id>/review/', views.mark_alert_reviewed, name='mark_alert_reviewed'),
]