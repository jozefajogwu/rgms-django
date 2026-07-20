from django.contrib import admin
from django.contrib import messages
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html, mark_safe
from django import forms
from .models import Patient, VitalReading, Alert, CaregiverAssignment, Doctor, Caregiver, DoctorAssignment
from .utils import send_patient_registration_email


# ============================================
# CUSTOM USER ADMIN (For Users section)
# ============================================
class CustomUserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_roles', 'is_staff')
    list_filter = ('groups', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    def get_roles(self, obj):
        roles = obj.groups.all()
        if roles:
            return ", ".join([g.name for g in roles])
        return "No Role"
    get_roles.short_description = "Roles"


# ============================================
# DOCTOR ADMIN - FIXED
# ============================================
@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    """
    Simplified Doctor management under Monitoring section
    """
    list_display = ('username', 'get_full_name', 'email', 'get_patient_count', 'is_active')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    list_filter = ('is_active', 'is_staff')
    
    fieldsets = (
        ('Doctor Information', {
            'fields': ('username', 'first_name', 'last_name', 'email')
        }),
        ('Password', {
            'fields': ('password',),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active', 'is_staff')
        }),
        ('Groups', {
            'fields': ('groups',),
            'description': 'Select "Doctors" group to assign doctor role'
        }),
    )
    
    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username
    get_full_name.short_description = "Full Name"
    
    def get_patient_count(self, obj):
        return Patient.objects.filter(assigned_doctor=obj).count()
    get_patient_count.short_description = "Patients"
    
    def save_model(self, request, obj, form, change):
        """
        Save the doctor user properly with groups after saving
        """
        # If this is a new user, create it first without groups
        if not obj.pk:
            # Set password if provided
            password = form.cleaned_data.get('password')
            if password:
                obj.set_password(password)
            else:
                obj.set_password('changeme123')
            
            # Set staff status
            obj.is_staff = True
            
            # SAVE FIRST to get an ID
            obj.save()
            
            # NOW add the groups after the user has an ID
            doctors_group, _ = Group.objects.get_or_create(name='Doctors')
            obj.groups.add(doctors_group)
        else:
            # For existing users, just save
            if form.cleaned_data.get('password'):
                obj.set_password(form.cleaned_data.get('password'))
            
            # Ensure they're in the Doctors group
            if not obj.groups.filter(name='Doctors').exists():
                doctors_group, _ = Group.objects.get_or_create(name='Doctors')
                obj.groups.add(doctors_group)
            
            obj.save()
    
    def save_form(self, request, form, change):
        return form.save(commit=False)
    
    def get_queryset(self, request):
        return super().get_queryset(request).filter(groups__name='Doctors')
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not obj:
            form.base_fields['password'].required = True
        else:
            form.base_fields['password'].required = False
            form.base_fields['password'].help_text = "Leave blank to keep current password"
        return form


# ============================================
# CAREGIVER ADMIN - FIXED
# ============================================
@admin.register(Caregiver)
class CaregiverAdmin(admin.ModelAdmin):
    """
    Simplified Caregiver management under Monitoring section
    """
    list_display = ('username', 'get_full_name', 'email', 'get_patient_count', 'is_active')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    list_filter = ('is_active', 'is_staff')
    
    fieldsets = (
        ('Caregiver Information', {
            'fields': ('username', 'first_name', 'last_name', 'email')
        }),
        ('Password', {
            'fields': ('password',),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active', 'is_staff')
        }),
        ('Groups', {
            'fields': ('groups',),
            'description': 'Select "Caregivers" group to assign caregiver role'
        }),
    )
    
    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username
    get_full_name.short_description = "Full Name"
    
    def get_patient_count(self, obj):
        return Patient.objects.filter(assigned_caregiver=obj).count()
    get_patient_count.short_description = "Patients"
    
    def save_model(self, request, obj, form, change):
        """
        Save the caregiver user properly with groups after saving
        """
        # If this is a new user, create it first without groups
        if not obj.pk:
            # Set password if provided
            password = form.cleaned_data.get('password')
            if password:
                obj.set_password(password)
            else:
                obj.set_password('changeme123')
            
            # Set staff status
            obj.is_staff = True
            
            # SAVE FIRST to get an ID
            obj.save()
            
            # NOW add the groups after the user has an ID
            caregivers_group, _ = Group.objects.get_or_create(name='Caregivers')
            obj.groups.add(caregivers_group)
        else:
            # For existing users, just save
            if form.cleaned_data.get('password'):
                obj.set_password(form.cleaned_data.get('password'))
            
            # Ensure they're in the Caregivers group
            if not obj.groups.filter(name='Caregivers').exists():
                caregivers_group, _ = Group.objects.get_or_create(name='Caregivers')
                obj.groups.add(caregivers_group)
            
            obj.save()
    
    def save_form(self, request, form, change):
        return form.save(commit=False)
    
    def get_queryset(self, request):
        return super().get_queryset(request).filter(groups__name='Caregivers')
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not obj:
            form.base_fields['password'].required = True
        else:
            form.base_fields['password'].required = False
            form.base_fields['password'].help_text = "Leave blank to keep current password"
        return form


# ============================================
# PATIENT ADMIN FORM (Creates user account automatically)
# ============================================
class PatientAdminForm(forms.ModelForm):
    create_account = forms.BooleanField(
        required=False,
        initial=True,
        label="Create login account",
        help_text="Creates a username and password so they can login"
    )
    username = forms.CharField(
        max_length=150,
        required=False,
        help_text="Leave blank to auto-generate"
    )
    password = forms.CharField(
        widget=forms.PasswordInput,
        required=False,
        help_text="Leave blank to auto-generate"
    )
    
    class Meta:
        model = Patient
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.user:
            self.initial['username'] = self.instance.user.username
            self.initial['create_account'] = False
            self.fields['username'].disabled = True
            self.fields['create_account'].help_text = "This person already has a login account"
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username:
            existing = User.objects.filter(username=username)
            if self.instance and self.instance.user:
                existing = existing.exclude(id=self.instance.user.id)
            if existing.exists():
                raise forms.ValidationError(f"Username '{username}' already exists. Please choose another.")
        return username
    
    def save(self, commit=True):
        patient = super().save(commit=False)
        
        create_account = self.cleaned_data.get('create_account', False)
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        
        if create_account and not patient.user:
            if not username:
                username = self._generate_username(patient.full_name)
            if not password:
                password = self._generate_password()
            
            user = User.objects.create_user(
                username=username,
                password=password,
                email=patient.email or '',
                first_name=patient.full_name.split()[0] if patient.full_name else '',
                last_name=' '.join(patient.full_name.split()[1:]) if len(patient.full_name.split()) > 1 else '',
            )
            user.is_staff = False
            user.save()
            patient.user = user
            
            self._user_created = True
            self._username = username
            self._password = password
        
        if commit:
            patient.save()
            self.save_m2m()
        
        return patient
    
    def _generate_username(self, full_name):
        import re
        base = re.sub(r'[^a-zA-Z0-9]', '_', full_name.lower())
        username = base
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base}_{counter}"
            counter += 1
        return username
    
    def _generate_password(self):
        """Generate a secure random password"""
        import random
        import string
        characters = string.ascii_letters + string.digits + '!@#$%^&*()_+-='
        password = ''.join(random.choice(characters) for _ in range(12))
        return password


# ============================================
# PATIENT ADMIN
# ============================================
@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    form = PatientAdminForm
    
    list_display = (
        'full_name',
        'email',
        'get_username',
        'phone_number',
        'get_roles',
        'get_doctor',
        'get_caregiver',
        'created_at',
    )
    search_fields = ('full_name', 'phone_number', 'email', 'user__username')
    list_filter = ('gender', 'care_type', 'assigned_doctor', 'assigned_caregiver')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('full_name', 'email', 'date_of_birth', 'gender', 'phone_number', 'address')
        }),
        ('Login Account', {
            'fields': ('create_account', 'username', 'password'),
            'description': 'Check "Create login account" to auto-generate login credentials'
        }),
        ('Roles', {
            'fields': ('is_patient', 'is_caregiver', 'is_client', 'can_self_report'),
            'description': 'Select all roles that apply'
        }),
        ('Care Team', {
            'fields': ('assigned_doctor', 'assigned_caregiver')
        }),
        ('Caregiver Responsibilities', {
            'fields': ('patients_caring_for',),
            'classes': ('collapse',)
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
        if obj and obj.user:
            return obj.user.username
        return "No account"
    get_username.short_description = "Username"
    
    def get_roles(self, obj):
        roles = []
        if obj.is_patient:
            roles.append("Patient")
        if obj.is_caregiver:
            roles.append("Caregiver")
        if obj.is_client:
            roles.append("Client")
        return ", ".join(roles) if roles else "None"
    get_roles.short_description = "Roles"
    
    def get_doctor(self, obj):
        if obj.assigned_doctor:
            return obj.assigned_doctor.get_full_name() or obj.assigned_doctor.username
        return "—"
    get_doctor.short_description = "Doctor"
    
    def get_caregiver(self, obj):
        if obj.assigned_caregiver:
            return obj.assigned_caregiver.get_full_name() or obj.assigned_caregiver.username
        return "—"
    get_caregiver.short_description = "Caregiver"
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        
        if hasattr(form, '_user_created') and form._user_created:
            self.message_user(
                request,
                f"✅ Account created! Username: {form._username}, Password: {form._password}",
                messages.SUCCESS
            )


# ============================================
# DOCTOR ASSIGNMENT ADMIN
# ============================================
@admin.register(DoctorAssignment)
class DoctorAssignmentAdmin(admin.ModelAdmin):
    list_display = ('get_doctor', 'get_patient', 'assignment_type', 'is_active', 'started_at')
    list_filter = ('assignment_type', 'is_active')
    search_fields = ('doctor__username', 'patient__full_name')
    
    fieldsets = (
        ('Assignment', {
            'fields': ('doctor', 'patient', 'assignment_type')
        }),
        ('Status', {
            'fields': ('is_active', 'ended_at')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
    )
    
    def get_doctor(self, obj):
        return obj.doctor.get_full_name() or obj.doctor.username
    get_doctor.short_description = "Doctor"
    
    def get_patient(self, obj):
        return obj.patient.full_name
    get_patient.short_description = "Patient"


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
# VITAL READING ADMIN
# ============================================
@admin.register(VitalReading)
class VitalReadingAdmin(admin.ModelAdmin):
    list_display = ('patient', 'systolic_bp', 'diastolic_bp', 'pulse_rate', 'created_at')
    search_fields = ('patient__full_name',)
    list_filter = ('created_at',)
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)


# ============================================
# ALERT ADMIN
# ============================================
@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('patient', 'severity', 'status', 'title', 'created_at')
    search_fields = ('patient__full_name', 'title')
    list_filter = ('severity', 'status', 'created_at')
    readonly_fields = ('created_at',)


# ============================================
# REGISTER USER ADMIN
# ============================================
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass
admin.site.register(User, CustomUserAdmin)