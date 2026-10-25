from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Count, Avg, Q
from django.http import JsonResponse
from datetime import timedelta
from collections import defaultdict
import json
import logging

from .forms import VitalReadingForm, AlertActionForm, AlertActionSimpleForm
from .models import Patient, VitalReading, Alert, Doctor, Caregiver, AlertAction
from .email_utils import send_vital_alert_email

logger = logging.getLogger(__name__)


# ============================================
# SMALL HELPERS
# ============================================
def _num(v):
    """Convert a model value (int/Decimal/None) to float or None."""
    return float(v) if v is not None else None


def _avg(values):
    """Average of non-empty values, or None if there are none."""
    vals = [float(v) for v in values if v is not None]
    return round(sum(vals) / len(vals), 1) if vals else None


def _daily_chart_series(readings):
    """
    Group readings by local calendar day and average each vital.
    Missing values are skipped (not counted as zero).
    """
    daily = defaultdict(list)
    for r in readings:
        daily[timezone.localtime(r.created_at).strftime('%Y-%m-%d')].append(r)

    series = {
        'labels': [], 'systolic': [], 'diastolic': [],
        'pulse': [], 'spo2': [], 'sugar': [],
    }
    for day in sorted(daily):
        rs = daily[day]
        series['labels'].append(day)
        series['systolic'].append(_avg(r.systolic_bp for r in rs))
        series['diastolic'].append(_avg(r.diastolic_bp for r in rs))
        series['pulse'].append(_avg(r.pulse_rate for r in rs))
        series['spo2'].append(_avg(r.oxygen_saturation for r in rs))
        series['sugar'].append(_avg(r.fasting_blood_sugar for r in rs))
    return series


def _chart_context(series):
    """
    Dashboard chart context as JSON strings, so None becomes null and
    templates can keep using {{ value|safe }} inside <script>.
    """
    return {
        'bp_labels': json.dumps(series['labels']),
        'systolic_data': json.dumps(series['systolic']),
        'diastolic_data': json.dumps(series['diastolic']),
        'pulse_data': json.dumps(series['pulse']),
        'spo2_data': json.dumps(series['spo2']),
        'sugar_data': json.dumps(series['sugar']),
        'has_chart_data': bool(series['labels']),
    }


def landing_page(request):
    return render(request, 'landing.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect_user_by_role(request, request.user)

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect_user_by_role(request, user)
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    return redirect('home')


def redirect_user_by_role(request, user):
    """Redirect users based on their role using Doctor and Caregiver models"""
    if user.is_superuser:
        return redirect('admin:index')

    if Doctor.objects.filter(user=user).exists():
        return redirect('doctor_dashboard')

    if Caregiver.objects.filter(user=user).exists():
        return redirect('caregiver_dashboard')

    if Patient.objects.filter(user=user).exists():
        return redirect('caregiver_dashboard')

    messages.warning(request, 'No role found for this account.')
    return redirect('home')


def get_patient_chart_data(patient, days=7):
    """Chart data + summary stats for one patient over the last `days` days."""
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)

    readings = list(
        VitalReading.objects.filter(
            patient=patient,
            created_at__gte=start_date,
            created_at__lte=end_date,
        ).order_by('created_at')
    )

    chart_data = {
        'labels':    [timezone.localtime(r.created_at).strftime('%b %d, %H:%M') for r in readings],
        'systolic':  [_num(r.systolic_bp) for r in readings],
        'diastolic': [_num(r.diastolic_bp) for r in readings],
        'pulse':     [_num(r.pulse_rate) for r in readings],
        'spo2':      [_num(r.oxygen_saturation) for r in readings],
        'sugar':     [_num(r.fasting_blood_sugar) for r in readings],
    }

    systolic = [v for v in chart_data['systolic'] if v is not None]
    if len(systolic) >= 2 and systolic[-1] > systolic[0]:
        trend = 'up'
    elif len(systolic) >= 2 and systolic[-1] < systolic[0]:
        trend = 'down'
    else:
        trend = 'stable'

    stats = {
        'avg_systolic':  _avg(chart_data['systolic']) or 0,
        'avg_diastolic': _avg(chart_data['diastolic']) or 0,
        'avg_pulse':     _avg(chart_data['pulse']) or 0,
        'avg_spo2':      _avg(chart_data['spo2']) or 0,
        'avg_sugar':     _avg(chart_data['sugar']) or 0,
        'trend':         trend,
        'readings_count': len(readings),
        'latest_reading': readings[-1] if readings else None,
    }

    return chart_data, stats


def is_doctor_authorized(doctor_user, patient):
    """Check if doctor is authorized to view this patient"""
    try:
        doctor = Doctor.objects.get(user=doctor_user)
        return patient.assigned_doctor == doctor
    except Doctor.DoesNotExist:
        return False


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

    # CHART DATA (real data only; no placeholder values)
    end_date = timezone.now()
    start_date = end_date - timedelta(days=7)

    recent_readings = VitalReading.objects.filter(
        patient__in=patients,
        created_at__gte=start_date,
        created_at__lte=end_date
    ).order_by('created_at')

    series = _daily_chart_series(recent_readings)

    # PATIENT INSIGHTS
    patient_insights = []
    for patient in patients:
        latest_reading = VitalReading.objects.filter(patient=patient).order_by('-created_at').first()
        alert_count = Alert.objects.filter(patient=patient, status='unreviewed').count()

        risk_score = 0

        if latest_reading:
            if latest_reading.systolic_bp > VitalReading.NORMAL_SYSTOLIC_MAX:
                risk_score += 2
            if latest_reading.diastolic_bp > VitalReading.NORMAL_DIASTOLIC_MAX:
                risk_score += 2
            if latest_reading.pulse_rate > VitalReading.NORMAL_PULSE_MAX:
                risk_score += 1
            if latest_reading.oxygen_saturation is not None and latest_reading.oxygen_saturation < VitalReading.NORMAL_SPO2_MIN:
                risk_score += 2
            if latest_reading.fasting_blood_sugar is not None and latest_reading.fasting_blood_sugar > VitalReading.NORMAL_FASTING_SUGAR_MAX:
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
            if latest.systolic_bp > VitalReading.NORMAL_SYSTOLIC_MAX:
                analysis_level = 'High'
            elif latest.systolic_bp > VitalReading.NORMAL_SYSTOLIC_MIN + 30:
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
        'patient_insights': patient_insights[:6],
        'live_patients': live_patients,
        'doctor': doctor,
        **_chart_context(series),
    }

    return render(request, 'doctor_dashboard.html', context)


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

    series = _daily_chart_series(self_recent_readings)

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
        **_chart_context(series),
    }

    return render(request, 'caregiver_dashboard.html', context)


# ============================================
# PATIENT RECORDS VIEW
# ============================================
@login_required(login_url='/login/')
def patient_records(request):
    """View for patients and caregivers to see their health records"""
    user = request.user

    try:
        patient = Patient.objects.get(user=user)
        is_patient = True
    except Patient.DoesNotExist:
        patient = None
        is_patient = False

    try:
        caregiver = Caregiver.objects.get(user=user)
        is_caregiver = True
    except Caregiver.DoesNotExist:
        caregiver = None
        is_caregiver = False

    if is_patient:
        vital_readings = VitalReading.objects.filter(patient=patient).order_by('-created_at')
        alerts = Alert.objects.filter(patient=patient).order_by('-created_at')

        context = {
            'is_patient': True,
            'is_caregiver': False,
            'patient': patient,
            'vital_readings': vital_readings,
            'alerts': alerts,
            'total_readings': vital_readings.count(),
            'total_alerts': alerts.count(),
            'active_alerts_count': alerts.filter(status='unreviewed').count(),
            'user': user,
        }
        return render(request, 'patient_records.html', context)

    elif is_caregiver:
        patients = Patient.objects.filter(assigned_caregiver=caregiver)

        all_readings = VitalReading.objects.filter(
            patient__in=patients
        ).order_by('-created_at')

        all_alerts = Alert.objects.filter(
            patient__in=patients
        ).order_by('-created_at')

        patient_data = []
        for p in patients:
            readings = VitalReading.objects.filter(patient=p).order_by('-created_at')
            alerts = Alert.objects.filter(patient=p).order_by('-created_at')
            patient_data.append({
                'patient': p,
                'readings': readings,
                'alerts': alerts,
                'total_readings': readings.count(),
                'total_alerts': alerts.count(),
                'active_alerts': alerts.filter(status='unreviewed').count(),
                'latest_reading': readings.first(),
            })

        context = {
            'is_patient': False,
            'is_caregiver': True,
            'caregiver': caregiver,
            'patients': patient_data,
            'total_patients': patients.count(),
            'total_readings': all_readings.count(),
            'total_alerts': all_alerts.count(),
            'user': user,
        }
        return render(request, 'caregiver_records.html', context)

    else:
        messages.error(request, 'You do not have any health records to view.')
        return redirect('home')


# ============================================
# CREATE ALERT FOR READING
# ============================================
def create_alert_for_reading(reading):
    """
    Create alerts for abnormal vital readings using the normal ranges
    from the VitalReading model
    """
    alerts_to_create = []

    # BLOOD PRESSURE
    if reading.systolic_bp < VitalReading.NORMAL_SYSTOLIC_MIN:
        alerts_to_create.append({
            'severity': 'warning',
            'title': 'Low Systolic BP Alert',
            'message': f'Systolic BP is {reading.systolic_bp} mmHg. Normal range is {VitalReading.NORMAL_SYSTOLIC_MIN}-{VitalReading.NORMAL_SYSTOLIC_MAX} mmHg.'
        })
    elif reading.systolic_bp > VitalReading.NORMAL_SYSTOLIC_MAX:
        alerts_to_create.append({
            'severity': 'warning',
            'title': 'High Systolic BP Alert',
            'message': f'Systolic BP is {reading.systolic_bp} mmHg. Normal range is {VitalReading.NORMAL_SYSTOLIC_MIN}-{VitalReading.NORMAL_SYSTOLIC_MAX} mmHg.'
        })

    if reading.diastolic_bp < VitalReading.NORMAL_DIASTOLIC_MIN:
        alerts_to_create.append({
            'severity': 'warning',
            'title': 'Low Diastolic BP Alert',
            'message': f'Diastolic BP is {reading.diastolic_bp} mmHg. Normal range is {VitalReading.NORMAL_DIASTOLIC_MIN}-{VitalReading.NORMAL_DIASTOLIC_MAX} mmHg.'
        })
    elif reading.diastolic_bp > VitalReading.NORMAL_DIASTOLIC_MAX:
        alerts_to_create.append({
            'severity': 'warning',
            'title': 'High Diastolic BP Alert',
            'message': f'Diastolic BP is {reading.diastolic_bp} mmHg. Normal range is {VitalReading.NORMAL_DIASTOLIC_MIN}-{VitalReading.NORMAL_DIASTOLIC_MAX} mmHg.'
        })

    # HEART RATE
    if reading.pulse_rate < VitalReading.NORMAL_PULSE_MIN:
        alerts_to_create.append({
            'severity': 'warning',
            'title': 'Low Heart Rate Alert',
            'message': f'Heart rate is {reading.pulse_rate} bpm. Normal range is {VitalReading.NORMAL_PULSE_MIN}-{VitalReading.NORMAL_PULSE_MAX} bpm.'
        })
    elif reading.pulse_rate > VitalReading.NORMAL_PULSE_MAX:
        alerts_to_create.append({
            'severity': 'warning',
            'title': 'High Heart Rate Alert',
            'message': f'Heart rate is {reading.pulse_rate} bpm. Normal range is {VitalReading.NORMAL_PULSE_MIN}-{VitalReading.NORMAL_PULSE_MAX} bpm.'
        })

    # OXYGEN SATURATION
    if reading.oxygen_saturation is not None:
        if reading.oxygen_saturation < VitalReading.NORMAL_SPO2_MIN:
            alerts_to_create.append({
                'severity': 'warning',
                'title': 'Low Oxygen Saturation Alert',
                'message': f'SpO2 is {reading.oxygen_saturation}%. Normal range is {VitalReading.NORMAL_SPO2_MIN}-{VitalReading.NORMAL_SPO2_MAX}%.'
            })
        elif reading.oxygen_saturation > VitalReading.NORMAL_SPO2_MAX:
            alerts_to_create.append({
                'severity': 'warning',
                'title': 'High Oxygen Saturation Alert',
                'message': f'SpO2 is {reading.oxygen_saturation}%. Normal range is {VitalReading.NORMAL_SPO2_MIN}-{VitalReading.NORMAL_SPO2_MAX}%.'
            })

    # FASTING BLOOD SUGAR
    if reading.fasting_blood_sugar is not None:
        if reading.fasting_blood_sugar < VitalReading.NORMAL_FASTING_SUGAR_MIN:
            alerts_to_create.append({
                'severity': 'warning',
                'title': 'Low Fasting Blood Sugar Alert',
                'message': f'Fasting blood sugar is {reading.fasting_blood_sugar} mg/dL. Normal range is {VitalReading.NORMAL_FASTING_SUGAR_MIN}-{VitalReading.NORMAL_FASTING_SUGAR_MAX} mg/dL.'
            })
        elif reading.fasting_blood_sugar > VitalReading.NORMAL_FASTING_SUGAR_MAX:
            alerts_to_create.append({
                'severity': 'warning',
                'title': 'High Fasting Blood Sugar Alert',
                'message': f'Fasting blood sugar is {reading.fasting_blood_sugar} mg/dL. Normal range is {VitalReading.NORMAL_FASTING_SUGAR_MIN}-{VitalReading.NORMAL_FASTING_SUGAR_MAX} mg/dL.'
            })

    # RANDOM BLOOD SUGAR
    if reading.random_blood_sugar is not None and reading.random_blood_sugar > VitalReading.NORMAL_RANDOM_SUGAR_MAX:
        alerts_to_create.append({
            'severity': 'warning',
            'title': 'High Random Blood Sugar Alert',
            'message': f'Random blood sugar is {reading.random_blood_sugar} mg/dL. Normal is below {VitalReading.NORMAL_RANDOM_SUGAR_MAX} mg/dL.'
        })

    # URINALYSIS
    if reading.urine_glucose and reading.urine_glucose != 'negative':
        alerts_to_create.append({
            'severity': 'warning',
            'title': 'Urine Glucose Alert',
            'message': f'Urine glucose is {reading.get_urine_glucose_display()}. Please review.'
        })

    if reading.urine_protein and reading.urine_protein != 'negative':
        alerts_to_create.append({
            'severity': 'warning',
            'title': 'Urine Protein Alert',
            'message': f'Urine protein is {reading.get_urine_protein_display()}. Please review.'
        })

    if reading.urine_acetone and reading.urine_acetone != 'negative':
        alerts_to_create.append({
            'severity': 'warning',
            'title': 'Urine Acetone/Ketone Alert',
            'message': f'Urine acetone is {reading.get_urine_acetone_display()}. Please review.'
        })

    if reading.urine_bilirubin and reading.urine_bilirubin != 'negative':
        alerts_to_create.append({
            'severity': 'warning',
            'title': 'Urine Bilirubin Alert',
            'message': f'Urine bilirubin is {reading.get_urine_bilirubin_display()}. Please review.'
        })

    if reading.urine_urobilinogen and reading.urine_urobilinogen != 'weakly_positive':
        alerts_to_create.append({
            'severity': 'warning',
            'title': 'Urobilinogen Alert',
            'message': f'Urobilinogen is {reading.get_urine_urobilinogen_display()}. Please review.'
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
            severity=alert_data['severity'],
            status='unreviewed'
        )


# ============================================
# ADD VITAL READING
# ============================================
@login_required
def add_vital_reading(request):
    """Client/Patient vital entry with doctor and admin notification"""

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

            alerts = Alert.objects.filter(reading=reading)
            has_alerts = alerts.exists()

            # EMAIL NOTIFICATIONS
            doctor_name = "your doctor"
            doctor_emails = []

            if reading.patient.assigned_doctor:
                doctor_user = reading.patient.assigned_doctor.user
                doctor_name = f"Dr. {doctor_user.get_full_name() or doctor_user.username}"
                if doctor_user.email:
                    doctor_emails.append(doctor_user.email)

            admin_emails = list(User.objects.filter(
                Q(is_superuser=True) | Q(is_staff=True)
            ).exclude(email='').values_list('email', flat=True))

            try:
                email_sent = send_vital_alert_email(
                    patient=reading.patient,
                    reading=reading,
                    alerts=alerts,
                    doctor_emails=doctor_emails,
                    admin_emails=admin_emails,
                    doctor_name=doctor_name
                )
                if email_sent:
                    logger.info(f"Vital alert email sent for {reading.patient.full_name}")
                else:
                    logger.warning(f"Vital alert email failed for {reading.patient.full_name}")
            except Exception as e:
                logger.error(f"Email error: {str(e)}")

            if has_alerts:
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
            'chart_json': json.dumps(chart_data),  # use {{ p.chart_json|safe }} in <script>
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
            'chart_json': json.dumps(chart_data),  # use {{ item.chart_json|safe }} in <script>
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


# ============================================
# PATIENT DETAIL VIEW
# ============================================
@login_required
def patient_detail(request, patient_id):
    """Display detailed information for a single patient"""
    user = request.user

    try:
        doctor = Doctor.objects.get(user=user)
    except Doctor.DoesNotExist:
        messages.error(request, 'You are not registered as a doctor.')
        return redirect('home')

    patient = get_object_or_404(Patient, id=patient_id)

    if patient.assigned_doctor != doctor:
        messages.error(request, 'You are not authorized to view this patient.')
        return redirect('doctor_patients_list')

    readings = VitalReading.objects.filter(patient=patient).order_by('-created_at')
    total_readings = readings.count()
    latest_reading = readings.first()

    active_alerts = Alert.objects.filter(patient=patient, status='unreviewed')

    # Chart data (last 30 days) — template reads it via {{ chart_data|json_script:"chart-data" }}
    chart_data, stats = get_patient_chart_data(patient, days=30)

    recent_readings = readings[:20]

    alert_actions = []
    for alert in active_alerts:
        actions = AlertAction.objects.filter(alert=alert).order_by('-created_at')
        alert_actions.append({
            'alert': alert,
            'actions': actions,
            'action_count': actions.count(),
            'latest_action': actions.first(),
        })

    context = {
        'patient': patient,
        'doctor': doctor,
        'readings': recent_readings,
        'total_readings': total_readings,
        'latest_reading': latest_reading,
        'active_alerts': active_alerts,
        'chart_data': chart_data,
        'stats': stats,
        'alert_count': active_alerts.count(),
        'alert_actions': alert_actions,
    }

    return render(request, 'patient_detail.html', context)


# ============================================
# PATIENT CLINICAL NOTE VIEW
# ============================================
@login_required
def add_patient_note(request, patient_id):
    """Add a clinical note for a patient (not tied to a specific alert)"""
    patient = get_object_or_404(Patient, id=patient_id)
    user = request.user

    if not is_doctor_authorized(user, patient):
        messages.error(request, 'You are not authorized to add notes for this patient.')
        return redirect('doctor_dashboard')

    if request.method == 'POST':
        action_type = request.POST.get('action_type')
        description = request.POST.get('description')
        notes = request.POST.get('notes')
        clinical_findings = request.POST.get('clinical_findings')
        assessment = request.POST.get('assessment')
        plan = request.POST.get('plan')
        follow_up_needed = request.POST.get('follow_up_needed') == 'on'
        follow_up_date = request.POST.get('follow_up_date')
        is_urgent = request.POST.get('is_urgent') == 'on'

        note_alert, created = Alert.objects.get_or_create(
            patient=patient,
            title='Clinical Note',
            severity='normal',
            status='reviewed',
            defaults={
                'message': f'Clinical note documented by Dr. {user.get_full_name()}',
                'reading': None,
            }
        )

        AlertAction.objects.create(
            alert=note_alert,
            doctor=user,
            action_type=action_type or 'other',
            description=description or 'Clinical note documented',
            notes=notes or '',
            clinical_findings=clinical_findings or '',
            assessment=assessment or '',
            plan=plan or '',
            follow_up_needed=follow_up_needed,
            follow_up_date=follow_up_date if follow_up_date else None,
        )

        if is_urgent:
            Alert.objects.create(
                patient=patient,
                reading=None,
                title='Urgent Clinical Note',
                message=description or 'Urgent clinical note documented',
                severity='critical',
                status='unreviewed'
            )

        messages.success(request, '✅ Clinical note documented successfully!')
        return redirect('patient_detail', patient_id=patient.id)

    context = {
        'patient': patient,
        'action_types': AlertAction.ACTION_CHOICES,
    }

    return render(request, 'add_patient_note.html', context)


# ============================================
# ALERT ACTION VIEWS - Clinical Documentation
# ============================================
@login_required
def alert_detail(request, alert_id):
    """View alert details and actions"""
    alert = get_object_or_404(Alert, id=alert_id)
    user = request.user

    if not is_doctor_authorized(user, alert.patient):
        messages.error(request, 'You are not authorized to view this alert.')
        return redirect('doctor_dashboard')

    actions = AlertAction.objects.filter(alert=alert).order_by('-created_at')

    try:
        doctor = Doctor.objects.get(user=user)
    except Doctor.DoesNotExist:
        messages.error(request, 'You are not registered as a doctor.')
        return redirect('home')

    context = {
        'alert': alert,
        'actions': actions,
        'patient': alert.patient,
        'doctor': doctor,
        'action_count': actions.count(),
    }

    return render(request, 'alert_detail.html', context)


@login_required
def add_alert_action(request, alert_id):
    """Add a clinical action for an alert"""
    alert = get_object_or_404(Alert, id=alert_id)
    user = request.user

    if not is_doctor_authorized(user, alert.patient):
        messages.error(request, 'You are not authorized to take action on this alert.')
        return redirect('doctor_dashboard')

    try:
        doctor = Doctor.objects.get(user=user)
    except Doctor.DoesNotExist:
        messages.error(request, 'You are not registered as a doctor.')
        return redirect('home')

    if request.method == 'POST':
        action_type = request.POST.get('action_type')
        description = request.POST.get('description', '').strip()
        notes = request.POST.get('notes', '').strip()
        clinical_findings = request.POST.get('clinical_findings', '').strip()
        assessment = request.POST.get('assessment', '').strip()
        plan = request.POST.get('plan', '').strip()
        follow_up_needed = request.POST.get('follow_up_needed') == 'on'
        follow_up_date = request.POST.get('follow_up_date')

        if not action_type:
            messages.error(request, 'Please select an action type.')
            return redirect('alert_detail', alert_id=alert.id)

        if not description:
            messages.error(request, 'Please provide a description of the action taken.')
            return redirect('alert_detail', alert_id=alert.id)

        try:
            action = AlertAction.objects.create(
                alert=alert,
                doctor=user,
                action_type=action_type,
                description=description,
                notes=notes or '',
                clinical_findings=clinical_findings or '',
                assessment=assessment or '',
                plan=plan or '',
                follow_up_needed=follow_up_needed,
                follow_up_date=follow_up_date if follow_up_date else None,
            )

            if action_type == 'resolved':
                alert.status = 'resolved'
                alert.reviewed_at = timezone.now()
                alert.reviewed_by = user
                alert.save()
                messages.success(request, '✅ Alert resolved and action documented successfully!')
            else:
                if alert.status == 'unreviewed':
                    alert.status = 'reviewed'
                    alert.reviewed_at = timezone.now()
                    alert.reviewed_by = user
                    alert.save()
                messages.success(request, f'✅ Action "{action.get_action_type_display()}" documented successfully!')

            return redirect('alert_detail', alert_id=alert.id)

        except Exception as e:
            logger.error(f"Error creating alert action: {str(e)}")
            messages.error(request, f'Error saving action: {str(e)}')
            return redirect('alert_detail', alert_id=alert.id)

    context = {
        'alert': alert,
        'patient': alert.patient,
        'doctor': doctor,
        'action_types': AlertAction.ACTION_CHOICES,
    }

    return render(request, 'add_alert_action.html', context)


# ============================================
# QUICK ACTION VIEW - For Triage Desk AJAX
# ============================================
@login_required
def add_quick_action(request, alert_id):
    """Add a quick action via AJAX from triage desk"""
    alert = get_object_or_404(Alert, id=alert_id)
    user = request.user

    if not is_doctor_authorized(user, alert.patient):
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)

    if request.method == 'POST':
        form = AlertActionSimpleForm(request.POST)
        if form.is_valid():
            action = form.save(commit=False)
            action.alert = alert
            action.doctor = user
            action.save()

            if form.cleaned_data.get('action_type') == 'resolved':
                alert.status = 'reviewed'
                alert.reviewed_at = timezone.now()
                alert.reviewed_by = user
                alert.save()

            return JsonResponse({
                'success': True,
                'action_id': action.id,
                'action_type': action.get_action_type_display(),
                'description': action.description,
                'notes': action.notes,
                'doctor': action.doctor.get_full_name() or action.doctor.username,
                'time': timezone.localtime(action.created_at).strftime('%Y-%m-%d %H:%M'),
            })
        else:
            return JsonResponse({'success': False, 'errors': str(form.errors)}, status=400)

    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=405)


@login_required
def get_alert_actions(request, alert_id):
    """Get actions for an alert via AJAX"""
    alert = get_object_or_404(Alert, id=alert_id)
    user = request.user

    if not is_doctor_authorized(user, alert.patient):
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)

    actions = AlertAction.objects.filter(alert=alert).order_by('-created_at')

    data = []
    for action in actions:
        data.append({
            'id': action.id,
            'action_type': action.get_action_type_display(),
            'description': action.description,
            'notes': action.notes,
            'doctor': action.doctor.get_full_name() or action.doctor.username,
            'time': timezone.localtime(action.created_at).strftime('%Y-%m-%d %H:%M'),
            'follow_up_needed': action.follow_up_needed,
            'follow_up_date': action.follow_up_date.strftime('%Y-%m-%d %H:%M') if action.follow_up_date else None,
        })

    return JsonResponse({'success': True, 'actions': data, 'count': len(data)})


# ============================================
# PATIENT FEEDBACK VIEW
# ============================================
@login_required
def patient_feedback(request):
    """Show feedback/clinical actions from doctors to the patient"""
    user = request.user

    try:
        patient = Patient.objects.get(user=user)
    except Patient.DoesNotExist:
        messages.error(request, 'No patient profile found.')
        return redirect('home')

    alerts = Alert.objects.filter(patient=patient).order_by('-created_at')

    alert_actions = []
    for alert in alerts:
        actions = AlertAction.objects.filter(alert=alert).order_by('-created_at')
        if actions.exists():
            alert_actions.append({
                'alert': alert,
                'actions': actions,
                'latest_action': actions.first(),
                'action_count': actions.count(),
            })

    latest_reading = VitalReading.objects.filter(patient=patient).order_by('-created_at').first()
    active_alerts_count = Alert.objects.filter(patient=patient, status='unreviewed').count()

    context = {
        'patient': patient,
        'alert_actions': alert_actions,
        'latest_reading': latest_reading,
        'active_alerts_count': active_alerts_count,
        'total_alerts': alerts.count(),
        'total_actions': sum(a['action_count'] for a in alert_actions),
        'assigned_doctor': patient.assigned_doctor,
        'assigned_caregiver': patient.assigned_caregiver,
        'user': user,
    }

    return render(request, 'patient_feedback.html', context)