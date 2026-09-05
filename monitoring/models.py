# monitoring/models.py - UPDATED with Normal Range Constants

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class Patient(models.Model):
    """
    Unified Patient/Caregiver/Client Model
    One person can be all three roles simultaneously
    """
    
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
    ]

    CARE_TYPE_CHOICES = [
        ('in_patient', 'In-patient Care'),
        ('outpatient', 'Outpatient Clinic'),
        ('home_care', 'Home Care'),
        ('self_care', 'Self Care'),  # Added for self-reporting patients
    ]

    # ============================================
    # LINK TO USER ACCOUNT (for login access)
    # ============================================
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='client_profile',
        help_text="User account for this client (for login access)"
    )
    
    # ============================================
    # PERSONAL INFORMATION
    # ============================================
    full_name = models.CharField(max_length=150)
    email = models.EmailField(blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    phone_number = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)

    # ============================================
    # EMERGENCY CONTACT
    # ============================================
    emergency_contact_name = models.CharField(max_length=150, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)

    # ============================================
    # ROLE FLAGS - The person can be all roles
    # ============================================
    is_patient = models.BooleanField(
        default=True,
        help_text="Is this person receiving care?"
    )
    
    is_caregiver = models.BooleanField(
        default=False,
        help_text="Is this person providing care to others?"
    )
    
    is_client = models.BooleanField(
        default=True,
        help_text="Is this person a client of the service?"
    )
    
    can_self_report = models.BooleanField(
        default=True,
        help_text="Can this person enter their own vitals?"
    )

    # ============================================
    # CARE TEAM (Who cares for this person)
    # ============================================
    assigned_doctor = models.ForeignKey(
        'Doctor',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='doctor_patients',
        help_text="The doctor assigned to this patient"
    )

    assigned_caregiver = models.ForeignKey(
        'Caregiver',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='caregiver_patients',
        help_text="The caregiver assigned to this patient"
    )
    
    # ============================================
    # CAREGIVER RESPONSIBILITIES
    # ============================================
    patients_caring_for = models.ManyToManyField(
        'self',
        symmetrical=False,
        blank=True,
        related_name='caregivers',
        help_text="If this person is a caregiver, who do they care for?"
    )

    # ============================================
    # MEDICAL INFORMATION
    # ============================================
    known_conditions = models.TextField(blank=True)
    current_medications = models.TextField(blank=True)
    care_type = models.CharField(
        max_length=20,
        choices=CARE_TYPE_CHOICES,
        default='home_care'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.full_name
    
    def get_role_display(self):
        """Get a human-readable role description"""
        roles = []
        if self.is_patient:
            roles.append("Patient")
        if self.is_caregiver:
            roles.append("Caregiver")
        if self.is_client:
            roles.append("Client")
        return " / ".join(roles) if roles else "Unknown"
    
    def get_user_or_create(self):
        """Get or create a user account for this client"""
        if self.user:
            return self.user
        
        import re
        from django.contrib.auth.models import User
        
        username = re.sub(r'[^a-zA-Z0-9]', '_', self.full_name.lower())
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}_{counter}"
            counter += 1
        
        user = User.objects.create_user(
            username=username,
            email=self.email or '',
            first_name=self.full_name.split()[0] if self.full_name else '',
            last_name=' '.join(self.full_name.split()[1:]) if len(self.full_name.split()) > 1 else '',
        )
        
        user.set_password('changeme123')
        user.save()
        
        self.user = user
        self.save()
        
        return user


class VitalReading(models.Model):
    """
    Vital signs reading - can be entered by patient or caregiver
    """
    
    # ============================================
    # NORMAL RANGE CONSTANTS
    # ============================================
    NORMAL_SYSTOLIC_MIN = 100
    NORMAL_SYSTOLIC_MAX = 140
    NORMAL_DIASTOLIC_MIN = 60
    NORMAL_DIASTOLIC_MAX = 90
    NORMAL_PULSE_MIN = 60
    NORMAL_PULSE_MAX = 100
    NORMAL_SPO2_MIN = 95
    NORMAL_SPO2_MAX = 100
    NORMAL_FASTING_SUGAR_MIN = 70
    NORMAL_FASTING_SUGAR_MAX = 126
    NORMAL_RANDOM_SUGAR_MAX = 200
    
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='vital_readings'
    )
    
    entered_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='entered_readings',
        help_text="Who entered this reading (patient or caregiver)"
    )
    
    SOURCE_CHOICES = [
        ('patient_self', 'Patient Self-Reported'),
        ('caregiver', 'Caregiver Entered'),
        ('doctor', 'Doctor Entered'),
        ('auto', 'Automated Device'),
    ]
    
    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default='patient_self',
        help_text="How was this reading collected?"
    )

    # ============================================
    # VITAL SIGNS
    # ============================================
    fasting_blood_sugar = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(1000)]
    )

    random_blood_sugar = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(1000)]
    )

    systolic_bp = models.PositiveIntegerField(
        validators=[MinValueValidator(50), MaxValueValidator(300)]
    )

    diastolic_bp = models.PositiveIntegerField(
        validators=[MinValueValidator(30), MaxValueValidator(200)]
    )

    pulse_rate = models.PositiveIntegerField(
        validators=[MinValueValidator(30), MaxValueValidator(250)]
    )

    oxygen_saturation = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(50), MaxValueValidator(100)],
        help_text="SpO2 percentage"
    )

    symptoms = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    report_file = models.FileField(upload_to='reports/', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ============================================
    # URINALYSIS FIELDS
    # ============================================
    URINE_RESULT_CHOICES = [
        ('negative', 'Negative'),
        ('trace', 'Trace'),
        ('plus', '+'),
        ('plus_2', '++'),
        ('plus_3', '+++'),
        ('plus_4', '++++'),
    ]

    NITRITE_CHOICES = [
        ('negative', 'Negative'),
        ('positive', 'Positive'),
    ]

    UROBILINOGEN_CHOICES = [
        ('weakly_positive', 'Weakly Positive'),
        ('plus', '+'),
        ('plus_2', '++'),
        ('plus_3', '+++'),
        ('plus_4', '++++'),
    ]

    urine_glucose = models.CharField(
        max_length=20,
        choices=URINE_RESULT_CHOICES,
        blank=True,
        null=True,
        default=None,
        help_text="Leave empty if not tested"
    )

    urine_protein = models.CharField(
        max_length=20,
        choices=URINE_RESULT_CHOICES,
        blank=True,
        null=True,
        default=None,
        help_text="Leave empty if not tested"
    )

    urine_acetone = models.CharField(
        max_length=20,
        choices=URINE_RESULT_CHOICES,
        blank=True,
        null=True,
        default=None,
        help_text="Leave empty if not tested"
    )

    urine_bilirubin = models.CharField(
        max_length=20,
        choices=URINE_RESULT_CHOICES,
        blank=True,
        null=True,
        default=None,
        help_text="Leave empty if not tested"
    )

    urine_urobilinogen = models.CharField(
        max_length=30,
        choices=UROBILINOGEN_CHOICES,
        blank=True,
        null=True,
        default=None,
        help_text="Leave empty if not tested"
    )

    urine_nitrite = models.CharField(
        max_length=20,
        choices=NITRITE_CHOICES,
        blank=True,
        null=True,
        default=None,
        help_text="Leave empty if not tested"
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.patient.full_name} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
    def is_abnormal(self):
        """
        Check if any vital signs are abnormal using the defined normal ranges
        """
        abnormalities = []
        
        # Blood Pressure Check (Systolic: 100-140, Diastolic: 60-90)
        if self.systolic_bp < self.NORMAL_SYSTOLIC_MIN or self.systolic_bp > self.NORMAL_SYSTOLIC_MAX:
            abnormalities.append(f"Systolic BP {self.systolic_bp} (Normal: {self.NORMAL_SYSTOLIC_MIN}-{self.NORMAL_SYSTOLIC_MAX} mmHg)")
        
        if self.diastolic_bp < self.NORMAL_DIASTOLIC_MIN or self.diastolic_bp > self.NORMAL_DIASTOLIC_MAX:
            abnormalities.append(f"Diastolic BP {self.diastolic_bp} (Normal: {self.NORMAL_DIASTOLIC_MIN}-{self.NORMAL_DIASTOLIC_MAX} mmHg)")
        
        # Heart Rate Check (60-100 bpm)
        if self.pulse_rate < self.NORMAL_PULSE_MIN or self.pulse_rate > self.NORMAL_PULSE_MAX:
            abnormalities.append(f"Heart Rate {self.pulse_rate} bpm (Normal: {self.NORMAL_PULSE_MIN}-{self.NORMAL_PULSE_MAX} bpm)")
        
        # Oxygen Saturation Check (95-100%)
        if self.oxygen_saturation and (self.oxygen_saturation < self.NORMAL_SPO2_MIN or self.oxygen_saturation > self.NORMAL_SPO2_MAX):
            abnormalities.append(f"SpO2 {self.oxygen_saturation}% (Normal: {self.NORMAL_SPO2_MIN}-{self.NORMAL_SPO2_MAX}%)")
        
        # Fasting Blood Sugar Check (70-126 mg/dL)
        if self.fasting_blood_sugar:
            if self.fasting_blood_sugar < self.NORMAL_FASTING_SUGAR_MIN or self.fasting_blood_sugar > self.NORMAL_FASTING_SUGAR_MAX:
                abnormalities.append(f"Fasting Sugar {self.fasting_blood_sugar} mg/dL (Normal: {self.NORMAL_FASTING_SUGAR_MIN}-{self.NORMAL_FASTING_SUGAR_MAX} mg/dL)")
        
        # Random Blood Sugar Check (< 200 mg/dL)
        if self.random_blood_sugar and self.random_blood_sugar > self.NORMAL_RANDOM_SUGAR_MAX:
            abnormalities.append(f"Random Sugar {self.random_blood_sugar} mg/dL (Normal: < {self.NORMAL_RANDOM_SUGAR_MAX} mg/dL)")
        
        return abnormalities
    
    def get_abnormal_count(self):
        """Return the number of abnormal vitals"""
        return len(self.is_abnormal())
    
    def is_abnormal_systolic(self):
        """Check if systolic BP is abnormal"""
        return self.systolic_bp < self.NORMAL_SYSTOLIC_MIN or self.systolic_bp > self.NORMAL_SYSTOLIC_MAX
    
    def is_abnormal_diastolic(self):
        """Check if diastolic BP is abnormal"""
        return self.diastolic_bp < self.NORMAL_DIASTOLIC_MIN or self.diastolic_bp > self.NORMAL_DIASTOLIC_MAX
    
    def is_abnormal_pulse(self):
        """Check if pulse rate is abnormal"""
        return self.pulse_rate < self.NORMAL_PULSE_MIN or self.pulse_rate > self.NORMAL_PULSE_MAX
    
    def is_abnormal_spo2(self):
        """Check if SpO2 is abnormal"""
        return self.oxygen_saturation and (self.oxygen_saturation < self.NORMAL_SPO2_MIN or self.oxygen_saturation > self.NORMAL_SPO2_MAX)
    
    def is_abnormal_fasting_sugar(self):
        """Check if fasting blood sugar is abnormal"""
        return self.fasting_blood_sugar and (self.fasting_blood_sugar < self.NORMAL_FASTING_SUGAR_MIN or self.fasting_blood_sugar > self.NORMAL_FASTING_SUGAR_MAX)


# ============================================
# ✅ ALERT MODEL - SINGLE DEFINITION (with nullable reading)
# ============================================
class Alert(models.Model):
    """
    Alerts generated from vital readings
    - reading can be NULL for clinical notes
    """
    
    SEVERITY_CHOICES = [
        ('normal', 'Normal'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
    ]

    STATUS_CHOICES = [
        ('unreviewed', 'Unreviewed'),
        ('reviewed', 'Reviewed'),
        ('resolved', 'Resolved'),
    ]

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='alerts'
    )

    # ✅ NULLABLE - allows clinical notes without readings
    reading = models.ForeignKey(
        VitalReading,
        on_delete=models.CASCADE,
        null=True,      # ← NULL allowed
        blank=True,     # ← Form can leave blank
        related_name='alerts'
    )

    title = models.CharField(max_length=200)
    message = models.TextField()
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='normal')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='unreviewed'
    )

    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_alerts'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.patient.full_name} - {self.severity} - {self.title}"


class CaregiverAssignment(models.Model):
    """
    Track caregiver assignments and relationships
    """
    
    caregiver = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='caregiving_assignments',
        help_text="The person providing care"
    )
    
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='received_care_assignments',
        help_text="The person receiving care"
    )
    
    ASSIGNMENT_TYPE_CHOICES = [
        ('primary', 'Primary Caregiver'),
        ('secondary', 'Secondary Caregiver'),
        ('professional', 'Professional Caregiver'),
        ('family', 'Family Caregiver'),
        ('self', 'Self Care'),
    ]
    
    assignment_type = models.CharField(
        max_length=20,
        choices=ASSIGNMENT_TYPE_CHOICES,
        default='primary'
    )
    
    is_active = models.BooleanField(default=True)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['caregiver', 'patient']
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.caregiver.full_name} → {self.patient.full_name} ({self.get_assignment_type_display()})"


class DoctorAssignment(models.Model):
    """
    Track doctor assignments and relationships
    """
    
    doctor = models.ForeignKey(
        'Doctor',
        on_delete=models.CASCADE,
        related_name='doctor_assignments',
        help_text="The doctor providing care"
    )
    
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='doctor_assignments',
        help_text="The patient receiving care"
    )
    
    ASSIGNMENT_TYPE_CHOICES = [
        ('primary', 'Primary Care Physician'),
        ('specialist', 'Specialist'),
        ('consultant', 'Consultant'),
        ('temporary', 'Temporary/Stand-in'),
    ]
    
    assignment_type = models.CharField(
        max_length=20,
        choices=ASSIGNMENT_TYPE_CHOICES,
        default='primary'
    )
    
    is_active = models.BooleanField(default=True)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['doctor', 'patient']
        ordering = ['-started_at']
    
    def __str__(self):
        doctor_name = self.doctor.user.get_full_name() or self.doctor.user.username
        return f"Dr. {doctor_name} → {self.patient.full_name} ({self.get_assignment_type_display()})"


# ============================================
# DOCTOR MODEL
# ============================================
class Doctor(models.Model):
    """
    Doctor model - Regular model with its own table
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='doctor_profile'
    )
    specialty = models.CharField(max_length=100, blank=True)
    license_number = models.CharField(max_length=50, blank=True, unique=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.user.get_full_name() or self.user.username
    
    def get_full_name(self):
        return self.user.get_full_name()
    
    @property
    def username(self):
        return self.user.username
    
    @property
    def email(self):
        return self.user.email
    
    @property
    def first_name(self):
        return self.user.first_name
    
    @property
    def last_name(self):
        return self.user.last_name
    
    class Meta:
        verbose_name = "Doctor"
        verbose_name_plural = "Doctors"
        ordering = ['-created_at']


# ============================================
# CAREGIVER MODEL
# ============================================
class Caregiver(models.Model):
    """
    Caregiver model - Regular model with its own table
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='caregiver_profile'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.user.get_full_name() or self.user.username
    
    def get_full_name(self):
        return self.user.get_full_name()
    
    @property
    def username(self):
        return self.user.username
    
    @property
    def email(self):
        return self.user.email
    
    @property
    def first_name(self):
        return self.user.first_name
    
    @property
    def last_name(self):
        return self.user.last_name
    
    class Meta:
        verbose_name = "Caregiver"
        verbose_name_plural = "Caregivers"
        ordering = ['-created_at']


# ============================================
# ALERT ACTION MODEL - Clinical Documentation
# ============================================
class AlertAction(models.Model):
    """
    Track clinical actions taken for patient alerts
    """
    
    ACTION_CHOICES = [
        ('assessed', 'Patient Assessed'),
        ('monitored', 'Vitals Monitored'),
        ('medication', 'Medication Adjusted'),
        ('referred', 'Referred to Specialist'),
        ('contacted', 'Patient Contacted'),
        ('lab_test', 'Lab Test Ordered'),
        ('imaging', 'Imaging Ordered'),
        ('follow_up', 'Follow-up Scheduled'),
        ('escalated', 'Escalated to Emergency'),
        ('resolved', 'Resolved/Closed'),
        ('other', 'Other Action'),
    ]
    
    alert = models.ForeignKey(
        Alert,
        on_delete=models.CASCADE,
        related_name='actions'
    )
    doctor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='alert_actions'
    )
    action_type = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES
    )
    description = models.TextField(help_text="Describe the action taken")
    notes = models.TextField(blank=True, help_text="Additional notes or observations")
    
    clinical_findings = models.TextField(blank=True)
    assessment = models.TextField(blank=True)
    plan = models.TextField(blank=True)
    
    follow_up_needed = models.BooleanField(default=False)
    follow_up_date = models.DateTimeField(null=True, blank=True)
    follow_up_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.doctor.username} - {self.get_action_type_display()} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"