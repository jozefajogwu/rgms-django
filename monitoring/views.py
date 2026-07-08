from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Count, Avg, Q
from datetime import timedelta
from collections import defaultdict

from .forms import VitalReadingForm
from .models import Patient, VitalReading, Alert


def landing_page(request):
    return render(request, 'landing.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect_user_by_role(request.user)

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect_user_by_role(user)
        messages.error(request, 'Invalid username or password.')

    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    return redirect('home')


def redirect_user_by_role(user):
    if user.is_superuser or user.groups.filter(name='Doctors').exists():
        return redirect('doctor_dashboard')
    if user.groups.filter(name='Caregivers').exists():
        return redirect('caregiver_dashboard')
    return redirect('landing')


@login_required
def doctor_dashboard(request):
    # Get the current doctor
    doctor = request.user
    
    # Get all patients assigned to this doctor
    patients = Patient.objects.filter(assigned_doctor=doctor)
    total_patients = patients.count()
    
    # Get all readings for these patients
    readings = VitalReading.objects.filter(patient__in=patients).order_by('-created_at')
    total_readings = readings.count()
    
    # Get latest readings for each patient
    latest_readings = []
    for patient in patients:
        latest = VitalReading.objects.filter(patient=patient).order_by('-created_at').first()
        if latest:
            latest_readings.append(latest)
    
    # Get alerts
    urgent_alerts = Alert.objects.filter(
        patient__in=patients,
        status='active'
    ).exclude(severity='low').order_by('-created_at')[:10]
    
    critical_alerts_count = Alert.objects.filter(
        patient__in=patients,
        severity='critical',
        status='active'
    ).count()
    
    warning_alerts_count = Alert.objects.filter(
        patient__in=patients,
        severity='warning',
        status='active'
    ).count()
    
    # ============================================
    # CHART DATA PREPARATION
    # ============================================
    
    # Get data for the last 7 days
    end_date = timezone.now()
    start_date = end_date - timedelta(days=7)
    
    # Get readings for the last 7 days
    recent_readings = VitalReading.objects.filter(
        patient__in=patients,
        created_at__gte=start_date,
        created_at__lte=end_date
    ).order_by('created_at')
    
    # Prepare chart labels (dates)
    chart_labels = []
    systolic_data = []
    diastolic_data = []
    pulse_data = []
    spo2_data = []
    sugar_data = []
    
    # Group readings by day
    daily_readings = defaultdict(list)
    
    for reading in recent_readings:
        day_key = reading.created_at.strftime('%Y-%m-%d')
        daily_readings[day_key].append(reading)
    
    # Sort the days
    sorted_days = sorted(daily_readings.keys())
    
    for day in sorted_days:
        day_readings = daily_readings[day]
        chart_labels.append(day)
        
        # Calculate averages for each metric
        avg_systolic = sum(r.systolic_bp for r in day_readings if r.systolic_bp) / len(day_readings) if day_readings else 0
        avg_diastolic = sum(r.diastolic_bp for r in day_readings if r.diastolic_bp) / len(day_readings) if day_readings else 0
        avg_pulse = sum(r.pulse_rate for r in day_readings if r.pulse_rate) / len(day_readings) if day_readings else 0
        avg_spo2 = sum(r.oxygen_saturation for r in day_readings if r.oxygen_saturation) / len(day_readings) if day_readings else 0
        avg_sugar = sum(r.fasting_blood_sugar for r in day_readings if r.fasting_blood_sugar) / len(day_readings) if day_readings else 0
        
        systolic_data.append(round(avg_systolic, 1))
        diastolic_data.append(round(avg_diastolic, 1))
        pulse_data.append(round(avg_pulse, 1))
        spo2_data.append(round(avg_spo2, 1))
        sugar_data.append(round(avg_sugar, 1))
    
    # If no data, provide sample data
    if not chart_labels:
        chart_labels = ['Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5', 'Day 6', 'Day 7']
        systolic_data = [120, 118, 122, 125, 119, 121, 120]
        diastolic_data = [80, 78, 82, 85, 79, 81, 80]
        pulse_data = [72, 70, 75, 74, 71, 73, 72]
        spo2_data = [98, 97, 99, 98, 97, 98, 98]
        sugar_data = [95, 92, 98, 100, 94, 96, 95]
    
    context = {
        'total_patients': total_patients,
        'total_readings': total_readings,
        'latest_readings': latest_readings[:10],
        'urgent_alerts': urgent_alerts,
        'critical_alerts_count': critical_alerts_count,
        'warning_alerts_count': warning_alerts_count,
        # Chart data
        'bp_labels': chart_labels,
        'systolic_data': systolic_data,
        'diastolic_data': diastolic_data,
        'pulse_data': pulse_data,
        'spo2_data': spo2_data,
        'sugar_data': sugar_data,
    }
    
    return render(request, 'doctor_dashboard.html', context)


# ============================================
# ADD CAREGIVER DASHBOARD HERE
# ============================================
@login_required
def caregiver_dashboard(request):
    assigned_patients = Patient.objects.filter(assigned_caregiver=request.user)
    recent_readings = VitalReading.objects.filter(
        patient__assigned_caregiver=request.user
    ).select_related('patient').order_by('-created_at')[:5]

    return render(request, 'caregiver_dashboard.html', {
        'assigned_patients': assigned_patients,
        'recent_readings': recent_readings,
    })


def create_alert_for_reading(reading):
    alerts_to_create = []

    # Blood Pressure
    if reading.systolic_bp >= 141 or reading.diastolic_bp >= 90:
        alerts_to_create.append({
            'severity': 'warning',
            'title': 'High Blood Pressure Alert',
            'message': 'The patient blood pressure reading is above the accepted limit.'
        })

    # Blood Sugar
    if reading.fasting_blood_sugar and reading.fasting_blood_sugar >= 6.5:
        alerts_to_create.append({
            'severity': 'warning',
            'title': 'Fasting Blood Sugar Alert',
            'message': 'The patient fasting blood sugar is 6.5 mmol/L or above.'
        })

    if reading.random_blood_sugar and reading.random_blood_sugar >= 8.3:
        alerts_to_create.append({
            'severity': 'warning',
            'title': 'Random Blood Sugar Alert',
            'message': 'The patient random blood sugar is 8.3 mmol/L or above.'
        })

    # Oxygen Saturation
    if reading.oxygen_saturation and reading.oxygen_saturation <= 94:
        alerts_to_create.append({
            'severity': 'warning',
            'title': 'Low Oxygen Saturation Alert',
            'message': 'The patient SpO2 reading is 94% or below.'
        })

    # Urinalysis
    if reading.urine_glucose != 'negative':
        alerts_to_create.append({
            'severity': 'warning',
            'title': 'Urine Glucose Alert',
            'message': 'Urine glucose is positive. This may require clinical review.'
        })

    if reading.urine_protein != 'negative':
        alerts_to_create.append({
            'severity': 'warning',
            'title': 'Urine Protein Alert',
            'message': 'Urine protein is positive. This may suggest kidney-related concern.'
        })

    if reading.urine_acetone != 'negative':
        alerts_to_create.append({
            'severity': 'warning',
            'title': 'Urine Acetone/Ketone Alert',
            'message': 'Urine acetone/ketone is positive. This may require clinical review.'
        })

    if reading.urine_bilirubin != 'negative':
        alerts_to_create.append({
            'severity': 'warning',
            'title': 'Urine Bilirubin Alert',
            'message': 'Urine bilirubin is positive. This may require clinical review.'
        })

    if reading.urine_urobilinogen != 'weakly_positive':
        alerts_to_create.append({
            'severity': 'warning',
            'title': 'Urobilinogen Alert',
            'message': 'Urobilinogen is above the expected weakly positive level.'
        })

    if reading.urine_nitrite == 'positive':
        alerts_to_create.append({
            'severity': 'warning',
            'title': 'Urine Nitrite Alert',
            'message': 'Urine nitrite is positive. This may suggest urinary tract infection.'
        })

    # Create alert objects
    for alert_data in alerts_to_create:
        Alert.objects.create(
            patient=reading.patient,
            reading=reading,
            title=alert_data['title'],
            message=alert_data['message'],
            severity=alert_data['severity']
        )


@login_required
def add_vital_reading(request):
    if request.method == 'POST':
        form = VitalReadingForm(request.POST)
        if form.is_valid():
            reading = form.save()
            create_alert_for_reading(reading)
            messages.success(request, 'Vital reading submitted successfully.')
            return redirect('caregiver_dashboard')
    else:
        form = VitalReadingForm()

    return render(request, 'add_vital_reading.html', {'form': form})


@login_required
def mark_alert_reviewed(request, alert_id):
    """Mark an alert as reviewed"""
    alert = get_object_or_404(Alert, id=alert_id)

    if request.method == 'POST':
        alert.status = 'reviewed'
        alert.reviewed_at = timezone.now()
        alert.reviewed_by = request.user
        alert.save()
        messages.success(request, f'Alert for {alert.patient.full_name} has been reviewed and cleared.')
        return redirect('doctor_dashboard')

    return redirect('doctor_dashboard')