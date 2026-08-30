from django.contrib import admin
from django.contrib import messages
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import Q
from django.utils.html import format_html, mark_safe
from django import forms
from .models import Patient, VitalReading, Alert, CaregiverAssignment, Doctor, Caregiver, DoctorAssignment
from .email_utils import send_registration_email


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
# DOCTOR ADMIN - UPDATED WITH EMAIL
# ============================================
class DoctorForm(forms.ModelForm):
    """Form for creating/editing doctors with user account"""
    username = forms.CharField(max_length=150, required=True)
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=True)  # ✅ Changed to required
    password = forms.CharField(
        widget=forms.PasswordInput,
        required=False,
        help_text="Leave blank to auto-generate a secure password"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput,
        required=False,
        help_text="Confirm password"
    )
    send_email = forms.BooleanField(
        required=False,
        initial=True,
        label="📧 Send welcome email to doctor",
        help_text="Uncheck to skip email notification"
    )
    
    class Meta:
        model = Doctor
        fields = ['specialty', 'license_number', 'is_active']
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username:
            existing = User.objects.filter(username=username)
            if self.instance and self.instance.pk and self.instance.user:
                existing = existing.exclude(id=self.instance.user.id)
            if existing.exists():
                raise forms.ValidationError(f"Username '{username}' already exists.")
        return username
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")
        
        # Auto-generate password if not provided
        if not self.instance.pk and not password:
            import random
            import string
            characters = string.ascii_letters + string.digits + '!@#$%^&*'
            cleaned_data['password'] = ''.join(random.choice(characters) for _ in range(12))
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Get the password before saving
        password = self.cleaned_data.get('password')
        send_email = self.cleaned_data.get('send_email', True)
        
        if self.instance.pk:
            # Update existing doctor
            user = self.instance.user
            user.username = self.cleaned_data['username']
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            user.email = self.cleaned_data['email']
            if password:
                user.set_password(password)
            user.is_staff = True
            user.save()
        else:
            # Create new user
            user = User.objects.create_user(
                username=self.cleaned_data['username'],
                first_name=self.cleaned_data['first_name'],
                last_name=self.cleaned_data['last_name'],
                email=self.cleaned_data['email'],
                password=password,
            )
            user.is_staff = True
            user.save()
            instance.user = user
            
            # Add to Doctors group
            doctors_group, _ = Group.objects.get_or_create(name='Doctors')
            user.groups.add(doctors_group)
            
            # ✅ Send welcome email
            if send_email and user.email:
                try:
                    send_registration_email(user, password, 'doctor')
                    self._email_sent = True
                except Exception as e:
                    self._email_error = str(e)
            self._password = password
        
        if commit:
            instance.save()
        
        return instance


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    form = DoctorForm
    list_display = ('get_username', 'get_full_name', 'get_email', 'specialty', 'get_patient_count', 'is_active')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'user__email', 'specialty')
    list_filter = ('is_active', 'specialty')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('User Information', {
            'fields': ('username', 'first_name', 'last_name', 'email', 'password', 'confirm_password', 'send_email')
        }),
        ('Professional Information', {
            'fields': ('specialty', 'license_number')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_username(self, obj):
        return obj.user.username
    get_username.short_description = "Username"
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    get_full_name.short_description = "Full Name"
    
    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = "Email"
    
    def get_patient_count(self, obj):
        return Patient.objects.filter(assigned_doctor=obj).count()
    get_patient_count.short_description = "Patients"
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        
        # Show success message with email status
        if hasattr(form, '_email_sent') and form._email_sent:
            messages.success(
                request,
                f'✅ Doctor "{obj.get_full_name()}" created! Welcome email sent to {obj.user.email}.'
            )
        elif hasattr(form, '_email_error'):
            messages.warning(
                request,
                f'✅ Doctor "{obj.get_full_name()}" created! But email failed: {form._email_error}'
            )
        else:
            messages.success(request, f'✅ Doctor "{obj.get_full_name()}" saved successfully!')


# ============================================
# CAREGIVER ADMIN
# ============================================
class CaregiverForm(forms.ModelForm):
    """Form for creating/editing caregivers with user account"""
    username = forms.CharField(max_length=150, required=True)
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=False)
    password = forms.CharField(
        widget=forms.PasswordInput,
        required=False,
        help_text="Leave blank to keep current password"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput,
        required=False,
        help_text="Confirm password"
    )
    
    class Meta:
        model = Caregiver
        fields = ['is_active']
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username:
            existing = User.objects.filter(username=username)
            if self.instance and self.instance.pk and self.instance.user:
                existing = existing.exclude(id=self.instance.user.id)
            if existing.exists():
                raise forms.ValidationError(f"Username '{username}' already exists.")
        return username
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")
        
        if not self.instance.pk and not password:
            cleaned_data['password'] = 'changeme123'
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        if self.instance.pk:
            user = self.instance.user
            user.username = self.cleaned_data['username']
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            user.email = self.cleaned_data['email']
            if self.cleaned_data.get('password'):
                user.set_password(self.cleaned_data['password'])
            user.is_staff = True
            user.save()
        else:
            user = User.objects.create_user(
                username=self.cleaned_data['username'],
                first_name=self.cleaned_data['first_name'],
                last_name=self.cleaned_data['last_name'],
                email=self.cleaned_data['email'],
                password=self.cleaned_data['password'],
            )
            user.is_staff = True
            user.save()
            instance.user = user
        
        if commit:
            instance.save()
        return instance


@admin.register(Caregiver)
class CaregiverAdmin(admin.ModelAdmin):
    form = CaregiverForm
    list_display = ('get_username', 'get_full_name', 'get_email', 'get_patient_count', 'is_active')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'user__email')
    list_filter = ('is_active',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('User Information', {
            'fields': ('username', 'first_name', 'last_name', 'email', 'password', 'confirm_password')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_username(self, obj):
        return obj.user.username
    get_username.short_description = "Username"
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    get_full_name.short_description = "Full Name"
    
    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = "Email"
    
    def get_patient_count(self, obj):
        return Patient.objects.filter(assigned_caregiver=obj).count()
    get_patient_count.short_description = "Patients"
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        messages.success(request, f'✅ Caregiver "{obj.get_full_name()}" saved successfully!')


# ============================================
# PATIENT ADMIN FORM - UPDATED WITH EMAIL
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
    send_email = forms.BooleanField(
        required=False,
        initial=True,
        label="📧 Send welcome email to patient",
        help_text="Uncheck to skip email notification"
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
            self.fields['send_email'].initial = False
    
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
        send_email = self.cleaned_data.get('send_email', True)
        
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
            
            # Add to Patients group
            patients_group, _ = Group.objects.get_or_create(name='Patients')
            user.groups.add(patients_group)
            
            # ✅ Send welcome email
            if send_email and user.email:
                try:
                    # Get assigned doctor name if exists
                    assigned_doctor = None
                    if self.cleaned_data.get('assigned_doctor'):
                        assigned_doctor = self.cleaned_data['assigned_doctor'].get_full_name()
                    send_registration_email(user, password, 'patient', assigned_doctor)
                    self._email_sent = True
                except Exception as e:
                    self._email_error = str(e)
            
            self._user_created = True
            self._username = username
            self._password = password
        
        if commit:
            patient.save()
            self.save_m2m()
            self._assign_user_groups(patient)
        
        return patient
    
    def _assign_user_groups(self, patient):
        doctors_group, _ = Group.objects.get_or_create(name='Doctors')
        caregivers_group, _ = Group.objects.get_or_create(name='Caregivers')
        patients_group, _ = Group.objects.get_or_create(name='Patients')
        
        if patient.assigned_doctor:
            doctor_user = patient.assigned_doctor.user
            doctor_user.groups.add(doctors_group)
        
        if patient.assigned_caregiver:
            caregiver_user = patient.assigned_caregiver.user
            caregiver_user.groups.add(caregivers_group)
        
        if patient.is_caregiver and patient.user:
            patient.user.groups.add(caregivers_group)
    
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
        import random
        import string
        characters = string.ascii_letters + string.digits + '!@#$%^&*()_+-='
        password = ''.join(random.choice(characters) for _ in range(12))
        return password


# ============================================
# ✅ UPDATED: PATIENT ADMIN (With Email)
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
        'assigned_doctor',
        'assigned_caregiver',
        'created_at',
    )
    search_fields = ('full_name', 'phone_number', 'email', 'user__username')
    list_filter = ('gender', 'care_type', 'assigned_doctor', 'assigned_caregiver')
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ['assigned_doctor', 'assigned_caregiver']
    autocomplete_fields = ['assigned_doctor', 'assigned_caregiver']
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('full_name', 'email', 'date_of_birth', 'gender', 'phone_number', 'address')
        }),
        ('Login Account', {
            'fields': ('create_account', 'username', 'password', 'send_email'),
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
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        
        doctors_group, _ = Group.objects.get_or_create(name='Doctors')
        caregivers_group, _ = Group.objects.get_or_create(name='Caregivers')
        patients_group, _ = Group.objects.get_or_create(name='Patients')
        
        if obj.assigned_doctor:
            obj.assigned_doctor.user.groups.add(doctors_group)
        
        if obj.assigned_caregiver:
            obj.assigned_caregiver.user.groups.add(caregivers_group)
        
        if obj.is_caregiver and obj.user:
            obj.user.groups.add(caregivers_group)
        
        if obj.is_patient and obj.user:
            obj.user.groups.add(patients_group)
        
        # Show account creation message
        if hasattr(form, '_user_created') and form._user_created:
            self.message_user(
                request,
                f"✅ Account created! Username: {form._username}, Password: {form._password}",
                messages.SUCCESS
            )
        
        # Show email status
        if hasattr(form, '_email_sent') and form._email_sent:
            self.message_user(
                request,
                f"✅ Welcome email sent to {obj.email}",
                messages.SUCCESS
            )
        elif hasattr(form, '_email_error'):
            self.message_user(
                request,
                f"⚠️ Account created but email failed: {form._email_error}",
                messages.WARNING
            )


# ============================================
# DOCTORASSIGNMENT - HIDDEN FROM ADMIN
# ============================================
# We're NOT registering DoctorAssignment here
# because Patient.assigned_doctor is the single source of truth


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