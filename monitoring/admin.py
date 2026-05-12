from django.contrib import admin
from .models import Patient, VitalReading, Alert


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = (
        'full_name',
        'gender',
        'care_type',
        'assigned_doctor',
        'assigned_caregiver',
        'created_at',
    )
    search_fields = ('full_name', 'phone_number')
    list_filter = ('gender', 'care_type')


@admin.register(VitalReading)
class VitalReadingAdmin(admin.ModelAdmin):
    list_display = (
        'patient',
        'systolic_bp',
        'diastolic_bp',
        'pulse_rate',
        'fasting_blood_sugar',
        'random_blood_sugar',
        'created_at',
    )
    search_fields = ('patient__full_name',)
    list_filter = ('created_at',)


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = (
        'patient',
        'severity',
        'status',
        'title',
        'created_at',
    )
    search_fields = ('patient__full_name', 'title')
    list_filter = ('severity', 'status', 'created_at')