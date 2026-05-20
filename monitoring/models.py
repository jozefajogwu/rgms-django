from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class Patient(models.Model):
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
    ]

    CARE_TYPE_CHOICES = [
        ('in_patient', 'In-patient Care'),
        ('outpatient', 'Outpatient Clinic'),
        ('home_care', 'Home Care'),
    ]

    full_name = models.CharField(max_length=150)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    phone_number = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)

    emergency_contact_name = models.CharField(max_length=150, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)

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
        related_name='caregiver_patients'
    )

    known_conditions = models.TextField(blank=True)
    current_medications = models.TextField(blank=True)
    care_type = models.CharField(
        max_length=20,
        choices=CARE_TYPE_CHOICES,
        default='home_care'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name


class VitalReading(models.Model):
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='vital_readings'
    )

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

    # Urinalysis fields
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

    def __str__(self):
        return f"{self.patient.full_name} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class Alert(models.Model):
    SEVERITY_CHOICES = [
        ('normal', 'Normal'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
    ]

    STATUS_CHOICES = [
        ('unreviewed', 'Unreviewed'),
        ('reviewed', 'Reviewed'),
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

    def __str__(self):
        return f"{self.patient.full_name} - {self.severity}"