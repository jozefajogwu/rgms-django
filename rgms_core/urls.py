from django.contrib import admin
from django.urls import path

from monitoring import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.dashboard, name='home'),
    path('caregiver/add-reading/', views.add_vital_reading, name='add_vital_reading'),
     path('alerts/<int:alert_id>/review/', views.mark_alert_reviewed, name='mark_alert_reviewed'),
]