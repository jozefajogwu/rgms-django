from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from .forms import VitalReadingForm
from .models import Patient, VitalReading, Alert


def landing_page(request):
    return render(request, 'monitoring/landing.html')


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

    return render(request, 'monitoring/login.html')


def logout_view(request):
    logout(request)
    return redirect('landing')


def redirect_user_by_role(user):
    if user.is_superuser:
        return redirect('doctor_dashboard')

    if user.groups.filter(name='Doctors').exists():
        return redirect('doctor_dashboard')

    if user.groups.filter(name='Caregivers').exists():
        return redirect('caregiver_dashboard')

    return redirect('landing')


@login_required
def doctor_dashboard(request):
    total_patients = Patient.objects.count()
    total_readings = VitalReading.objects.count()

    critical_alerts_count = Alert.objects.filter(
        severity='critical',
        status='unreviewed'
    ).count()

    warning_alerts_count = Alert.objects.filter(
        severity='warning',
        status='unreviewed'
    ).count()

    latest_readings = VitalReading.objects.select_related('patient').order_by('-created_at')[:5]

    urgent_alerts = Alert.objects.select_related(
        'patient',
        'reading'
    ).filter(
        status='unreviewed'
    ).order_by('-created_at')[:10]

    return render(request, 'monitoring/doctor_dashboard.html', {
        'total_patients': total_patients,
        'total_readings': total_readings,
        'critical_alerts_count': critical_alerts_count,
        'warning_alerts_count': warning_alerts_count,
        'latest_readings': latest_readings,
        'urgent_alerts': urgent_alerts,
    })


@login_required
def caregiver_dashboard(request):
    assigned_patients = Patient.objects.filter(assigned_caregiver=request.user)
    recent_readings = VitalReading.objects.filter(
        patient__assigned_caregiver=request.user
    ).select_related('patient').order_by('-created_at')[:5]

    return render(request, 'monitoring/caregiver_dashboard.html', {
        'assigned_patients': assigned_patients,
        'recent_readings': recent_readings,
    })


def create_alert_for_reading(reading):
    severity = None
    title = None
    message = None

    if reading.systolic_bp >= 180 or reading.diastolic_bp >= 120:
        severity = 'critical'
        title = 'Critical Blood Pressure Alert'
        message = 'The patient has a very high blood pressure reading.'

    elif reading.systolic_bp >= 140 or reading.diastolic_bp >= 90:
        severity = 'warning'
        title = 'High Blood Pressure Warning'
        message = 'The patient has an elevated blood pressure reading.'

    elif reading.pulse_rate >= 120 or reading.pulse_rate <= 45:
        severity = 'warning'
        title = 'Pulse Rate Warning'
        message = 'The patient has an unusual pulse rate reading.'

    elif reading.fasting_blood_sugar and reading.fasting_blood_sugar >= 126:
        severity = 'warning'
        title = 'Fasting Blood Sugar Warning'
        message = 'The patient has an elevated fasting blood sugar reading.'

    elif reading.random_blood_sugar and reading.random_blood_sugar >= 200:
        severity = 'warning'
        title = 'Random Blood Sugar Warning'
        message = 'The patient has an elevated random blood sugar reading.'

    if severity:
        Alert.objects.create(
            patient=reading.patient,
            reading=reading,
            title=title,
            message=message,
            severity=severity
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

    return render(request, 'monitoring/add_vital_reading.html', {
        'form': form
    })


@login_required
def mark_alert_reviewed(request, alert_id):
    alert = get_object_or_404(Alert, id=alert_id)

    if request.method == 'POST':
        alert.status = 'reviewed'
        alert.reviewed_at = timezone.now()
        alert.reviewed_by = request.user
        alert.save()

        messages.success(request, 'Alert marked as reviewed.')
        return redirect('doctor_dashboard')

    return redirect('doctor_dashboard')