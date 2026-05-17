from django.contrib import admin
from django.urls import path

from monitoring import views

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', views.landing_page, name='landing'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    path('doctor/dashboard/', views.doctor_dashboard, name='doctor_dashboard'),
    path('caregiver/dashboard/', views.caregiver_dashboard, name='caregiver_dashboard'),

    path('caregiver/add-reading/', views.add_vital_reading, name='add_vital_reading'),
    path('alerts/<int:alert_id>/review/', views.mark_alert_reviewed, name='mark_alert_reviewed'),
]