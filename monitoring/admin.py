from django.contrib import admin
from django.contrib import messages
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django import forms
from .models import Patient, VitalReading, Alert, CaregiverAssignment
from .utils import send_patient_registration_email


# ============================================
# PATIENT ADMIN FORM WITH USER CREATION
# ============================================
class PatientAdminForm(forms.ModelForm):
    """Custom form for Patient admin that includes user creation fields"""
    
    # Add username and password fields
    username = forms.CharField(
        max_length=150,
        required=False,
        help_text="Leave blank to auto-generate from full name"
    )
    password = forms.CharField(
        widget=forms.PasswordInput,
        required=False,
        help_text="Leave blank to auto-generate a random password"
    )
    send_login_email = forms.BooleanField(
        required=False,
        initial=True,
        help_text="Send login credentials to the patient's email"
    )
    
    class Meta:
        model = Patient
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If editing an existing patient with a user, show the username
        if self.instance and self.instance.pk and self.instance.user:
            self.initial['username'] = self.instance.user.username
    
    def clean_username(self):
        """Validate username if provided"""
        username = self.cleaned_data.get('username')
        if username:
            # Check if username exists (excluding current user if editing)
            existing_user = User.objects.filter(username=username)
            if self.instance and self.instance.user:
                existing_user = existing_user.exclude(id=self.instance.user.id)
            if existing_user.exists():
                raise forms.ValidationError(f"Username '{username}' already exists. Please choose another.")
        return username
    
    def save(self, commit=True):
        """Save patient and create user account if needed"""
        patient = super().save(commit=False)
        
        # Get form data
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        send_email = self.cleaned_data.get('send_login_email', True)
        
        # If user is not linked, create one
        if not patient.user:
            # Generate username if not provided
            if not username:
                username = self._generate_username(patient.full_name)
            
            # Generate password if not provided
            if not password:
                password = User.objects.make_random_password()
            
            # Create user
            user = User.objects.create_user(
                username=username,
                password=password,
                email=patient.email or '',
                first_name=patient.full_name.split()[0] if patient.full_name else '',
                last_name=' '.join(patient.full_name.split()[1:]) if len(patient.full_name.split()) > 1 else '',
            )
            user.is_staff = False  # Patients are not staff
            user.save()
            patient.user = user
            
            # Send email with credentials
            if send_email and patient.email:
                self._send_login_email(patient, username, password)
            
            # Store for later display
            self._user_created = True
            self._username = username
            self._password = password
        
        # Save the patient
        if commit:
            patient.save()
            self.save_m2m()
        
        return patient
    
    def _generate_username(self, full_name):
        """Generate a unique username from full name"""
        import re
        base = re.sub(r'[^a-zA-Z0-9]', '_', full_name.lower())
        username = base
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base}_{counter}"
            counter += 1
        return username
    
    def _send_login_email(self, patient, username, password):
        """Send login credentials to patient"""
        from django.core.mail import send_mail
        from django.conf import settings
        
        subject = f"Welcome to RGMS - Your Login Credentials"
        message = f"""
Dear {patient.full_name},

You have been registered in the Remote Geriatric Monitoring System (RGMS).

Your login credentials are:
Username: {username}
Password: {password}

Please login at: http://127.0.0.1:8000/login/

For security, please change your password after your first login.

Best regards,
RGMS Team
        """
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[patient.email],
                fail_silently=False,
            )
            return True
        except Exception as e:
            print(f"Could not send email: {e}")
            return False


# ============================================
# CUSTOM USER ADMIN
# ============================================
class CustomUserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_roles', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'groups')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('Role Assignment Help', {
            'fields': (),
            'description': '👨‍⚕️ To assign a role: Go to "Permissions" section above and add user to "Doctors" or "Caregivers" group.'
        }),
    )
    
    def get_roles(self, obj):
        roles = obj.groups.all()
        if roles:
            return ", ".join([g.name for g in roles])
        return "No Role"
    get_roles.short_description = "Roles"
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        
        if obj.is_staff and not obj.is_superuser and not obj.groups.exists():
            caregiver_group, _ = Group.objects.get_or_create(name='Caregivers')
            obj.groups.add(caregiver_group)
            self.message_user(
                request,
                f"ℹ️ User {obj.username} was automatically added to the 'Caregivers' group.",
                level='INFO'
            )


# ============================================
# PATIENT/CLIENT/CAREGIVER ADMIN
# ============================================
@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    form = PatientAdminForm
    
    list_display = (
        'full_name',
        'email',
        'get_username',
        'phone_number',
        'gender',
        'get_roles_display',
        'get_doctor_name',
        'get_caregiver_name',
        'created_at',
    )
    search_fields = ('full_name', 'phone_number', 'email', 'user__username')
    list_filter = ('gender', 'care_type', 'is_patient', 'is_caregiver', 'is_client', 'assigned_doctor', 'assigned_caregiver')
    
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('full_name', 'email', 'date_of_birth', 'gender', 'phone_number', 'address')
        }),
        ('User Account (Login Access)', {
            'fields': ('user', 'username', 'password', 'send_login_email'),
            'description': 'Create or link a user account for login access. Leave username/password blank to auto-generate.'
        }),
        ('Role Assignment (Patient = Caregiver = Client)', {
            'fields': ('is_patient', 'is_caregiver', 'is_client', 'can_self_report'),
            'description': 'Check all roles that apply to this person'
        }),
        ('Care Team - Doctor Assignment', {
            'fields': ('assigned_doctor',),
            'description': '👨‍⚕️ Assign a doctor to this patient/client'
        }),
        ('Care Team - Caregiver Assignment', {
            'fields': ('assigned_caregiver',),
            'description': '👩‍⚕️ Assign a caregiver to this patient/client'
        }),
        ('Caregiver Responsibilities (If this person is a caregiver)', {
            'fields': ('patients_caring_for',),
            'description': 'If this person is a caregiver, select who they care for'
        }),
        ('Emergency Contact', {
            'fields': ('emergency_contact_name', 'emergency_contact_phone'),
            'classes': ('collapse',)
        }),
        ('Medical Information', {
            'fields': ('known_conditions', 'current_medications', 'care_type'),
            'classes': ('collapse',)
        }),
    )
    
    def get_username(self, obj):
        if obj.user:
            return obj.user.username
        return "No Account"
    get_username.short_description = "Username"
    
    def get_roles_display(self, obj):
        return obj.get_role_display()
    get_roles_display.short_description = "Roles"
    
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
        
        if db_field.name == "user":
            existing_users = Patient.objects.filter(user__isnull=False).values_list('user_id', flat=True)
            kwargs["queryset"] = User.objects.exclude(id__in=existing_users)
        
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        
        # Send registration email if new patient
        if not change and obj.email:
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
        
        # If user was created, show credentials
        if hasattr(form, '_user_created') and form._user_created:
            self.message_user(
                request,
                f"🔑 User account created! Username: {form._username}, Password: {form._password}",
                messages.INFO
            )
    
    def save_form(self, request, form, change):
        """Save the form and return the object"""
        return form.save()


# ============================================
# VITAL READING ADMIN
# ============================================
@admin.register(VitalReading)
class VitalReadingAdmin(admin.ModelAdmin):
    list_display = (
        'patient',
        'get_source_badge',
        'systolic_bp',
        'diastolic_bp',
        'pulse_rate',
        'oxygen_saturation',
        'created_at',
    )
    search_fields = ('patient__full_name',)
    list_filter = ('created_at', 'source', 'patient__assigned_doctor')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at')
    
    def get_source_badge(self, obj):
        colors = {
            'patient_self': '#3b82f6',
            'caregiver': '#0d9488',
            'doctor': '#8b5cf6',
            'auto': '#f59e0b',
        }
        color = colors.get(obj.source, '#94a3b8')
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 10px;">{}</span>',
            color,
            obj.get_source_display()
        )
    get_source_badge.short_description = "Source"


# ============================================
# ALERT ADMIN
# ============================================
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
    readonly_fields = ('created_at',)


# ============================================
# CAREGIVER ASSIGNMENT ADMIN
# ============================================
@admin.register(CaregiverAssignment)
class CaregiverAssignmentAdmin(admin.ModelAdmin):
    list_display = ('caregiver', 'patient', 'assignment_type', 'is_active', 'started_at')
    list_filter = ('assignment_type', 'is_active')
    search_fields = ('caregiver__full_name', 'patient__full_name')
    readonly_fields = ('started_at',)


# ============================================
# REGISTER CUSTOM USER ADMIN
# ============================================
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass
admin.site.register(User, CustomUserAdmin)