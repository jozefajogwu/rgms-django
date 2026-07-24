from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Count, Avg, Q
from datetime import timedelta
from collections import defaultdict

from .forms import VitalReadingForm
from .models import Patient, VitalReading, Alert, Doctor, Caregiver


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
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    return redirect('home')


def redirect_user_by_role(user):
    """Redirect users based on their role using Doctor and Caregiver models"""
    if user.is_superuser:
        return redirect('admin:index')
    
    try:
        doctor = Doctor.objects.get(user=user)
        return redirect('doctor_dashboard')
    except Doctor.DoesNotExist:
        pass
    
    try:
        caregiver = Caregiver.objects.get(user=user)
        return redirect('caregiver_dashboard')
    except Caregiver.DoesNotExist:
        pass
    
    try:
        patient = Patient.objects.get(user=user)
        return redirect('caregiver_dashboard')
    except Patient.DoesNotExist:
        pass
    
    messages.warning(request, 'No role found for this account.')
    return redirect('home')


def get_patient_chart_data(patient, days=7):
    """Helper function to get chart data for a patient"""
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    readings = VitalReading.objects.filter(
        patient=patient,
        created_at__gte=start_date,
        created_at__lte=end_date
    ).order_by('created_at')
    
    chart_data = {
        'labels': [],
        'systolic': [],
        'diastolic': [],
        'pulse': [],
        'spo2': [],
        'sugar': [],
    }
    
    for reading in readings:
        chart_data['labels'].append(reading.created_at.strftime('%Y-%m-%d %H:%M'))
        chart_data['systolic'].append(float(reading.systolic_bp))
        chart_data['diastolic'].append(float(reading.diastolic_bp))
        chart_data['pulse'].append(float(reading.pulse_rate))
        chart_data['spo2'].append(float(reading.oxygen_saturation) if reading.oxygen_saturation else None)
        chart_data['sugar'].append(float(reading.fasting_blood_sugar) if reading.fasting_blood_sugar else None)
    
    stats = {
        'avg_systolic': round(sum(chart_data['systolic']) / len(chart_data['systolic']), 1) if chart_data['systolic'] else 0,
        'avg_diastolic': round(sum(chart_data['diastolic']) / len(chart_data['diastolic']), 1) if chart_data['diastolic'] else 0,
        'avg_pulse': round(sum(chart_data['pulse']) / len(chart_data['pulse']), 1) if chart_data['pulse'] else 0,
        'avg_spo2': round(sum([s for s in chart_data['spo2'] if s]) / len([s for s in chart_data['spo2'] if s]), 1) if chart_data['spo2'] else 0,
        'avg_sugar': round(sum([s for s in chart_data['sugar'] if s]) / len([s for s in chart_data['sugar'] if s]), 1) if chart_data['sugar'] else 0,
        'trend': 'up' if chart_data['systolic'] and chart_data['systolic'][-1] > chart_data['systolic'][0] else 'down' if chart_data['systolic'] and chart_data['systolic'][-1] < chart_data['systolic'][0] else 'stable',
        'readings_count': len(readings),
        'latest_reading': readings.first() if readings else None,
    }
    
    return chart_data, stats


@login_required
def doctor_dashboard(request):
    """Doctor dashboard - clinical view with charts"""
    user = request.user
    
    try:
        doctor = Doctor.objects.get(user=user)
    except Doctor.DoesNotExist:
        messages.error(request, 'You are not registered as a doctor.')
        return redirect('home')
    
    patients = Patient.objects.filter(assigned_doctor=doctor)
    total_patients = patients.count()
    
    readings = VitalReading.objects.filter(patient__in=patients).order_by('-created_at')
    total_readings = readings.count()
    
    latest_readings = []
    for patient in patients:
        latest = VitalReading.objects.filter(patient=patient).order_by('-created_at').first()
        if latest:
            latest_readings.append(latest)
    
    urgent_alerts = Alert.objects.filter(
        patient__in=patients,
        status='unreviewed'
    ).exclude(severity='normal').order_by('-created_at')[:10]
    
    critical_alerts_count = Alert.objects.filter(
        patient__in=patients,
        severity='critical',
        status='unreviewed'
    ).count()
    
    warning_alerts_count = Alert.objects.filter(
        patient__in=patients,
        severity='warning',
        status='unreviewed'
    ).count()
    
    # CHART DATA
    end_date = timezone.now()
    start_date = end_date - timedelta(days=7)
    
    recent_readings = VitalReading.objects.filter(
        patient__in=patients,
        created_at__gte=start_date,
        created_at__lte=end_date
    ).order_by('created_at')
    
    chart_labels = []
    systolic_data = []
    diastolic_data = []
    pulse_data = []
    spo2_data = []
    sugar_data = []
    
    daily_readings = defaultdict(list)
    
    for reading in recent_readings:
        day_key = reading.created_at.strftime('%Y-%m-%d')
        daily_readings[day_key].append(reading)
    
    sorted_days = sorted(daily_readings.keys())
    
    for day in sorted_days:
        day_readings = daily_readings[day]
        chart_labels.append(day)
        
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
    
    if not chart_labels:
        chart_labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        systolic_data = [120, 118, 122, 125, 119, 121, 120]
        diastolic_data = [80, 78, 82, 85, 79, 81, 80]
        pulse_data = [72, 70, 75, 74, 71, 73, 72]
        spo2_data = [98, 97, 99, 98, 97, 98, 98]
        sugar_data = [95, 92, 98, 100, 94, 96, 95]
    
    # PATIENT INSIGHTS
    patient_insights = []
    for patient in patients:
        latest_reading = VitalReading.objects.filter(patient=patient).order_by('-created_at').first()
        alert_count = Alert.objects.filter(patient=patient, status='unreviewed').count()
        
        risk_score = 0
        level = 'Low'
        
        if latest_reading:
            if latest_reading.systolic_bp > 140:
                risk_score += 2
            if latest_reading.diastolic_bp > 90:
                risk_score += 2
            if latest_reading.pulse_rate > 100:
                risk_score += 1
            if latest_reading.oxygen_saturation and latest_reading.oxygen_saturation < 95:
                risk_score += 2
            if latest_reading.fasting_blood_sugar and latest_reading.fasting_blood_sugar > 6.5:
                risk_score += 2
        
        risk_score += alert_count
        
        if risk_score >= 5:
            level = 'High'
        elif risk_score >= 3:
            level = 'Medium'
        else:
            level = 'Low'
        
        trend = 'stable'
        recent_readings_list = VitalReading.objects.filter(patient=patient).order_by('-created_at')[:2]
        if len(recent_readings_list) >= 2:
            if recent_readings_list[0].systolic_bp > recent_readings_list[1].systolic_bp:
                trend = 'up'
            elif recent_readings_list[0].systolic_bp < recent_readings_list[1].systolic_bp:
                trend = 'down'
        
        patient_insights.append({
            'patient': patient,
            'score': risk_score,
            'level': level,
            'trend': trend,
            'latest_reading': latest_reading,
            'alert_count': alert_count
        })
    
    patient_insights.sort(key=lambda x: x['score'], reverse=True)
    
    # LIVE PATIENTS
    live_patients = []
    for patient in patients:
        latest = VitalReading.objects.filter(patient=patient).order_by('-created_at').first()
        if latest:
            is_recent = (timezone.now() - latest.created_at).total_seconds() < 3600
            
            analysis_level = 'Normal'
            if latest.systolic_bp > 140:
                analysis_level = 'High'
            elif latest.systolic_bp > 130:
                analysis_level = 'Medium'
            
            if is_recent:
                live_patients.append({
                    'patient': patient,
                    'analysis': {
                        'score': latest.systolic_bp,
                        'level': analysis_level
                    },
                    'updated_at': latest.created_at
                })
    
    context = {
        'total_patients': total_patients,
        'total_readings': total_readings,
        'latest_readings': latest_readings[:10],
        'urgent_alerts': urgent_alerts,
        'critical_alerts_count': critical_alerts_count,
        'warning_alerts_count': warning_alerts_count,
        'bp_labels': chart_labels,
        'systolic_data': systolic_data,
        'diastolic_data': diastolic_data,
        'pulse_data': pulse_data,
        'spo2_data': spo2_data,
        'sugar_data': sugar_data,
        'patient_insights': patient_insights[:6],
        'live_patients': live_patients,
        'doctor': doctor,
    }
    
    return render(request, 'doctor_dashboard.html', context)


# ============================================
# NEW: DOCTOR PATIENTS LIST VIEW
# ============================================
@login_required
def doctor_patients_list(request):
    """Show all patients assigned to the logged-in doctor"""
    user = request.user
    
    try:
        doctor = Doctor.objects.get(user=user)
    except Doctor.DoesNotExist:
        messages.error(request, 'You are not registered as a doctor.')
        return redirect('home')
    
    patients = Patient.objects.filter(assigned_doctor=doctor)
    
    patient_data = []
    for patient in patients:
        latest_reading = VitalReading.objects.filter(patient=patient).order_by('-created_at').first()
        active_alerts = Alert.objects.filter(patient=patient, status='unreviewed')
        critical_alerts = active_alerts.filter(severity='critical')
        warning_alerts = active_alerts.filter(severity='warning')
        
        patient_data.append({
            'patient': patient,
            'latest_reading': latest_reading,
            'alert_count': active_alerts.count(),
            'has_critical': critical_alerts.exists(),
            'has_warning': warning_alerts.exists(),
            'status': 'critical' if critical_alerts.exists() else 'warning' if warning_alerts.exists() else 'stable'
        })
    
    context = {
        'patients': patient_data,
        'total_patients': patients.count(),
        'critical_count': sum(1 for p in patient_data if p['status'] == 'critical'),
        'warning_count': sum(1 for p in patient_data if p['status'] == 'warning'),
        'stable_count': sum(1 for p in patient_data if p['status'] == 'stable'),
        'doctor_name': doctor.user.get_full_name() or doctor.user.username,
    }
    
    return render(request, 'doctor_patients_list.html', context)


@login_required
def caregiver_dashboard(request):
    """Unified dashboard for Caregiver or Patient"""
    user = request.user
    
    try:
        caregiver = Caregiver.objects.get(user=user)
        patients = Patient.objects.filter(assigned_caregiver=caregiver)
        is_caregiver = True
    except Caregiver.DoesNotExist:
        is_caregiver = False
        patients = Patient.objects.none()
    
    try:
        patient_profile = Patient.objects.get(user=user)
        is_patient = True
    except Patient.DoesNotExist:
        patient_profile = None
        is_patient = False
    
    if is_patient:
        my_readings = VitalReading.objects.filter(patient=patient_profile).order_by('-created_at')
        total_my_readings = my_readings.count()
        latest_my_reading = my_readings.first()
        my_alerts = Alert.objects.filter(patient=patient_profile, status='unreviewed')
    else:
        my_readings = VitalReading.objects.none()
        total_my_readings = 0
        latest_my_reading = None
        my_alerts = Alert.objects.none()
    
    if is_caregiver:
        patients_readings = VitalReading.objects.filter(
            patient__in=patients
        ).order_by('-created_at')
        patient_alerts = Alert.objects.filter(
            patient__in=patients,
            status='unreviewed'
        )
        urgent_alerts = Alert.objects.filter(
            patient__in=patients,
            status='unreviewed'
        ).exclude(severity='normal').order_by('-created_at')[:10]
    else:
        patients_readings = VitalReading.objects.none()
        patient_alerts = Alert.objects.none()
        urgent_alerts = Alert.objects.none()
    
    total_alerts = my_alerts.count() + patient_alerts.count()
    
    end_date = timezone.now()
    start_date = end_date - timedelta(days=7)
    
    if is_patient:
        self_recent_readings = VitalReading.objects.filter(
            patient=patient_profile,
            created_at__gte=start_date,
            created_at__lte=end_date
        ).order_by('created_at')
    else:
        self_recent_readings = VitalReading.objects.none()
    
    chart_labels = []
    systolic_data = []
    diastolic_data = []
    pulse_data = []
    spo2_data = []
    sugar_data = []
    
    daily_readings = defaultdict(list)
    
    for reading in self_recent_readings:
        day_key = reading.created_at.strftime('%Y-%m-%d')
        daily_readings[day_key].append(reading)
    
    sorted_days = sorted(daily_readings.keys())
    
    for day in sorted_days:
        day_readings = daily_readings[day]
        chart_labels.append(day)
        
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
    
    if not chart_labels:
        chart_labels = ['Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5', 'Day 6', 'Day 7']
        systolic_data = [120, 118, 122, 125, 119, 121, 120]
        diastolic_data = [80, 78, 82, 85, 79, 81, 80]
        pulse_data = [72, 70, 75, 74, 71, 73, 72]
        spo2_data = [98, 97, 99, 98, 97, 98, 98]
        sugar_data = [95, 92, 98, 100, 94, 96, 95]
    
    context = {
        'client': patient_profile,
        'my_readings': my_readings[:20],
        'total_my_readings': total_my_readings,
        'latest_my_reading': latest_my_reading,
        'patients_caring_for': patients,
        'patients_readings': patients_readings[:10],
        'my_alerts': my_alerts,
        'patient_alerts': patient_alerts,
        'total_alerts': total_alerts,
        'urgent_alerts': urgent_alerts,
        'is_patient': is_patient,
        'is_caregiver': is_caregiver,
        'has_patients': patients.exists(),
        'bp_labels': chart_labels,
        'systolic_data': systolic_data,
        'diastolic_data': diastolic_data,
        'pulse_data': pulse_data,
        'spo2_data': spo2_data,
        'sugar_data': sugar_data,
    }
    
    return render(request, 'caregiver_dashboard.html', context)


def create_alert_for_reading(reading):
    alerts_to_create = []

    if reading.systolic_bp >= 141 or reading.diastolic_bp >= 90:
        alerts_to_create.append({
            'severity': 'warning',
            'title': 'High Blood Pressure Alert',
            'message': 'The patient blood pressure reading is above the accepted limit.'
        })

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

    if reading.oxygen_saturation and reading.oxygen_saturation <= 94:
        alerts_to_create.append({
            'severity': 'warning',
            'title': 'Low Oxygen Saturation Alert',
            'message': 'The patient SpO2 reading is 94% or below.'
        })

    if reading.urine_glucose and reading.urine_glucose != 'negative':
        alerts_to_create.append({
            'severity': 'warning',
            'title': 'Urine Glucose Alert',
            'message': 'Urine glucose is positive. This may require clinical review.'
        })

    if reading.urine_protein and reading.urine_protein != 'negative':
        alerts_to_create.append({
            'severity': 'warning',
            'title': 'Urine Protein Alert',
            'message': 'Urine protein is positive. This may suggest kidney-related concern.'
        })

    if reading.urine_acetone and reading.urine_acetone != 'negative':
        alerts_to_create.append({
            'severity': 'warning',
            'title': 'Urine Acetone/Ketone Alert',
            'message': 'Urine acetone/ketone is positive. This may require clinical review.'
        })

    if reading.urine_bilirubin and reading.urine_bilirubin != 'negative':
        alerts_to_create.append({
            'severity': 'warning',
            'title': 'Urine Bilirubin Alert',
            'message': 'Urine bilirubin is positive. This may require clinical review.'
        })

    if reading.urine_urobilinogen and reading.urine_urobilinogen != 'weakly_positive':
        alerts_to_create.append({
            'severity': 'warning',
            'title': 'Urobilinogen Alert',
            'message': 'Urobilinogen is above the expected weakly positive level.'
        })

    if reading.urine_nitrite and reading.urine_nitrite == 'positive':
        alerts_to_create.append({
            'severity': 'warning',
            'title': 'Urine Nitrite Alert',
            'message': 'Urine nitrite is positive. This may suggest urinary tract infection.'
        })

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
    """Client/Patient vital entry with doctor notification"""
    
    try:
        client = Patient.objects.get(user=request.user)
    except Patient.DoesNotExist:
        messages.error(request, 'No client profile found.')
        return redirect('home')
    
    if request.method == 'POST':
        post_data = request.POST.copy()
        post_data['patient'] = client.id
        
        form = VitalReadingForm(post_data)
        
        if form.is_valid():
            reading = form.save(commit=False)
            reading.patient = client
            reading.source = 'patient_self'
            reading.entered_by = request.user
            reading.save()
            
            create_alert_for_reading(reading)
            
            doctor_name = "your doctor"
            if reading.patient.assigned_doctor:
                doctor_name = f"Dr. {reading.patient.assigned_doctor.user.get_full_name() or reading.patient.assigned_doctor.user.username}"
            
            alerts_created = Alert.objects.filter(reading=reading).exists()
            
            if alerts_created:
                success_message = (
                    f'✅ Vital reading submitted successfully! '
                    f'{doctor_name} has been notified and will review your results.'
                )
                extra_message = (
                    '⚠️ Some values were outside normal range. '
                    'Your doctor will contact you if needed.'
                )
            else:
                success_message = (
                    f'✅ Vital reading submitted successfully! '
                    f'{doctor_name} has been notified.'
                )
                extra_message = 'All values are within normal range. Continue monitoring your health.'
            
            messages.success(request, success_message)
            messages.info(request, extra_message)
            
            return redirect('caregiver_dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = VitalReadingForm()

    return render(request, 'add_vital_reading.html', {
        'form': form,
        'client': client,
    })


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


# ============================================
# NEW: TRIAGE DESK VIEW
# ============================================
@login_required
def triage_desk(request):
    """Triage desk with detailed charts for clinical review"""
    user = request.user
    
    try:
        doctor = Doctor.objects.get(user=user)
    except Doctor.DoesNotExist:
        messages.error(request, 'You are not registered as a doctor.')
        return redirect('home')
    
    patients = Patient.objects.filter(assigned_doctor=doctor)
    
    critical_patients = []
    warning_patients = []
    stable_patients = []
    
    for patient in patients:
        active_alerts = Alert.objects.filter(patient=patient, status='unreviewed')
        critical_alerts = active_alerts.filter(severity='critical')
        warning_alerts = active_alerts.filter(severity='warning')
        latest_reading = VitalReading.objects.filter(patient=patient).order_by('-created_at').first()
        
        chart_data, stats = get_patient_chart_data(patient, days=14)
        
        patient_info = {
            'patient': patient,
            'latest_reading': latest_reading,
            'alerts': active_alerts,
            'alert_count': active_alerts.count(),
            'last_reading_time': latest_reading.created_at if latest_reading else None,
            'chart_data': chart_data,
            'stats': stats,
        }
        
        if critical_alerts.exists():
            patient_info['priority'] = 'critical'
            critical_patients.append(patient_info)
        elif warning_alerts.exists():
            patient_info['priority'] = 'warning'
            warning_patients.append(patient_info)
        else:
            patient_info['priority'] = 'stable'
            stable_patients.append(patient_info)
    
    context = {
        'critical_patients': critical_patients,
        'warning_patients': warning_patients,
        'stable_patients': stable_patients,
        'total_patients': patients.count(),
        'critical_count': len(critical_patients),
        'warning_count': len(warning_patients),
        'stable_count': len(stable_patients),
    }
    
    return render(request, 'triage_desk.html', context)


# ============================================
# NEW: LIVE TELEMETRY VIEW
# ============================================
@login_required
def live_telemetry(request):
    """Live telemetry dashboard with real-time charts"""
    user = request.user
    
    try:
        doctor = Doctor.objects.get(user=user)
    except Doctor.DoesNotExist:
        messages.error(request, 'You are not registered as a doctor.')
        return redirect('home')
    
    patients = Patient.objects.filter(assigned_doctor=doctor)
    
    telemetry_data = []
    critical_count = 0
    warning_count = 0
    stable_count = 0
    no_data_count = 0
    
    for patient in patients:
        latest_reading = VitalReading.objects.filter(patient=patient).order_by('-created_at').first()
        active_alerts = Alert.objects.filter(patient=patient, status='unreviewed')
        critical_alerts = active_alerts.filter(severity='critical')
        warning_alerts = active_alerts.filter(severity='warning')
        
        chart_data, stats = get_patient_chart_data(patient, days=7)
        
        if latest_reading:
            if critical_alerts.exists():
                status = 'critical'
                critical_count += 1
            elif warning_alerts.exists():
                status = 'warning'
                warning_count += 1
            else:
                status = 'stable'
                stable_count += 1
        else:
            status = 'no_data'
            no_data_count += 1
        
        telemetry_data.append({
            'patient': patient,
            'latest_reading': latest_reading,
            'alerts': active_alerts[:3],
            'status': status,
            'last_update': latest_reading.created_at if latest_reading else None,
            'has_reading': latest_reading is not None,
            'chart_data': chart_data,
            'stats': stats,
        })
    
    context = {
        'telemetry_data': telemetry_data,
        'total_patients': patients.count(),
        'critical_count': critical_count,
        'warning_count': warning_count,
        'stable_count': stable_count,
        'no_data_count': no_data_count,
        'doctor_name': doctor.user.get_full_name() or doctor.user.username,
    }
    
    return render(request, 'live_telemetry.html', context)

@login_required
def patient_detail(request, patient_id):
    """
    Display detailed information for a single patient
    """
    user = request.user
    
    # Get the Doctor instance for this user
    try:
        doctor = Doctor.objects.get(user=user)
    except Doctor.DoesNotExist:
        messages.error(request, 'You are not registered as a doctor.')
        return redirect('home')
    
    # Get the patient
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Check if this doctor is assigned to this patient
    if patient.assigned_doctor != doctor:
        messages.error(request, 'You are not authorized to view this patient.')
        return redirect('doctor_patients_list')
    
    # Get all readings for this patient
    readings = VitalReading.objects.filter(patient=patient).order_by('-created_at')
    total_readings = readings.count()
    
    # Get latest reading
    latest_reading = readings.first()
    
    # Get alerts for this patient
    active_alerts = Alert.objects.filter(patient=patient, status='unreviewed')
    resolved_alerts = Alert.objects.filter(patient=patient, status='reviewed')
    
    # Get chart data (last 30 days)
    chart_data, stats = get_patient_chart_data(patient, days=30)
    
    # Get readings for the table (last 20)
    recent_readings = readings[:20]
    
    # Check if patient has a user account
    has_account = patient.user is not None
    
    context = {
        'patient': patient,
        'doctor': doctor,
        'readings': recent_readings,
        'total_readings': total_readings,
        'latest_reading': latest_reading,
        'active_alerts': active_alerts,
        'resolved_alerts': resolved_alerts,
        'chart_data': chart_data,
        'stats': stats,
        'has_account': has_account,
        'alert_count': active_alerts.count(),
    }
    
    return render(request, 'patient_detail.html', context)