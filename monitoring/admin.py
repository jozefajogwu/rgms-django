from django.contrib import admin
from django.contrib import messages
from django.contrib.auth.models import User, Group
from django.utils.html import format_html
from .models import Patient, VitalReading, Alert
from .utils import send_patient_registration_email


# ============================================
# SIMPLE APPROACH: Don't override User admin
# Use default Django User admin
# ============================================

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = (
        'full_name',
        'email',
        'phone_number',
        'gender',
        'care_type',
        'get_doctor_name',
        'get_caregiver_name',
        'created_at',
    )
    search_fields = ('full_name', 'phone_number', 'email')
    list_filter = ('gender', 'care_type', 'assigned_doctor', 'assigned_caregiver')
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('full_name', 'email', 'date_of_birth', 'gender', 'phone_number', 'address')
        }),
        ('Emergency Contact', {
            'fields': ('emergency_contact_name', 'emergency_contact_phone')
        }),
        ('Care Team - Doctor Assignment', {
            'fields': ('assigned_doctor',),
            'description': '👨‍⚕️ Assign a doctor to this patient (only users in "Doctors" group shown)'
        }),
        ('Care Team - Caregiver Assignment', {
            'fields': ('assigned_caregiver',),
            'description': '👩‍⚕️ Assign a caregiver to this patient (only users in "Caregivers" group shown)'
        }),
        ('Care Type', {
            'fields': ('care_type',),
        }),
        ('Medical Information', {
            'fields': ('known_conditions', 'current_medications'),
            'classes': ('collapse',)
        }),
    )
    
    def get_doctor_name(self, obj):
        if obj.assigned_doctor:
            return obj.assigned_doctor.get_full_name() or obj.assigned_doctor.username
        return "Not Assigned"
    get_doctor_name.short_description = "Doctor"
    
    def get_caregiver_name(self, obj):
        if obj.assigned_caregiver:
            return obj.assigned_caregiver.get_full_name() or obj.assigned_caregiver.username
        return "Not Assigned"
    get_caregiver_name.short_description = "Caregiver"
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "assigned_doctor":
            try:
                doctors_group = Group.objects.get(name='Doctors')
                kwargs["queryset"] = User.objects.filter(groups=doctors_group).order_by('username')
            except Group.DoesNotExist:
                kwargs["queryset"] = User.objects.filter(is_staff=True).order_by('username')
        
        if db_field.name == "assigned_caregiver":
            try:
                caregivers_group = Group.objects.get(name='Caregivers')
                kwargs["queryset"] = User.objects.filter(groups=caregivers_group).order_by('username')
            except Group.DoesNotExist:
                kwargs["queryset"] = User.objects.filter(is_staff=True).order_by('username')
        
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        
        if not change:
            if obj.email:
                email_sent = send_patient_registration_email(obj)
                if email_sent:
                    self.message_user(
                        request, 
                        f"✅ Registration email sent to {obj.full_name} ({obj.email})", 
                        messages.SUCCESS
                    )
                else:
                    self.message_user(
                        request, 
                        f"❌ Could not send email to {obj.full_name}. Please check the email address.",
                        messages.ERROR
                    )
            else:
                self.message_user(
                    request,
                    f"⚠️ No email provided for {obj.full_name}. Email not sent.",
                    messages.WARNING
                )


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
    list_filter = ('created_at', 'patient__assigned_doctor')
    date_hierarchy = 'created_at'


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