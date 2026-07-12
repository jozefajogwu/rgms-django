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
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='doctor_patients'
    )

    assigned_caregiver = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='caregiver_patients',
        help_text="The person who provides care for this client"
    )
    
    # ============================================
    # CAREGIVER RESPONSIBILITIES (Who this person cares for)
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
        
        # Create a user account if one doesn't exist
        import re
        from django.contrib.auth.models import User
        
        # Generate username from full name
        username = re.sub(r'[^a-zA-Z0-9]', '_', self.full_name.lower())
        # Ensure uniqueness
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
        
        # Set password to something secure - user can change it later
        user.set_password('changeme123')
        user.save()
        
        self.user = user
        self.save()
        
        return user


class VitalReading(models.Model):
    """
    Vital signs reading - can be entered by patient or caregiver
    """
    
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='vital_readings'
    )
    
    # Who entered this reading?
    entered_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='entered_readings',
        help_text="Who entered this reading (patient or caregiver)"
    )
    
    # Source of the reading
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
        default='negative'
    )

    urine_protein = models.CharField(
        max_length=20,
        choices=URINE_RESULT_CHOICES,
        default='negative'
    )

    urine_acetone = models.CharField(
        max_length=20,
        choices=URINE_RESULT_CHOICES,
        default='negative'
    )

    urine_bilirubin = models.CharField(
        max_length=20,
        choices=URINE_RESULT_CHOICES,
        default='negative'
    )

    urine_urobilinogen = models.CharField(
        max_length=30,
        choices=UROBILINOGEN_CHOICES,
        default='weakly_positive'
    )

    urine_nitrite = models.CharField(
        max_length=20,
        choices=NITRITE_CHOICES,
        default='negative'
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.patient.full_name} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
    def is_abnormal(self):
        """Check if any vital signs are abnormal"""
        abnormalities = []
        
        # Blood pressure check
        if self.systolic_bp >= 141 or self.diastolic_bp >= 91:
            abnormalities.append("High Blood Pressure")
        
        # Heart rate check
        if self.pulse_rate > 100 or self.pulse_rate < 60:
            abnormalities.append("Abnormal Heart Rate")
        
        # Oxygen saturation check
        if self.oxygen_saturation and self.oxygen_saturation < 95:
            abnormalities.append("Low Oxygen Saturation")
        
        # Blood sugar check
        if self.fasting_blood_sugar and self.fasting_blood_sugar > 126:
            abnormalities.append("High Fasting Blood Sugar")
        elif self.fasting_blood_sugar and self.fasting_blood_sugar < 70:
            abnormalities.append("Low Fasting Blood Sugar")
        
        return abnormalities


class Alert(models.Model):
    """
    Alerts generated from vital readings
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

    reading = models.ForeignKey(
        VitalReading,
        on_delete=models.CASCADE,
        related_name='alerts'
    )

    title = models.CharField(max_length=150)
    message = models.TextField()
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='unreviewed'
    )

    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
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
        User,
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
        doctor_name = self.doctor.get_full_name() or self.doctor.username
        return f"Dr. {doctor_name} → {self.patient.full_name} ({self.get_assignment_type_display()})"


class Doctor(User):
    """Proxy model for Doctor users"""
    class Meta:
        proxy = True
        verbose_name = "Doctor"
        verbose_name_plural = "Doctors"


class Caregiver(User):
    """Proxy model for Caregiver users"""
    class Meta:
        proxy = True
        verbose_name = "Caregiver"
        verbose_name_plural = "Caregivers"