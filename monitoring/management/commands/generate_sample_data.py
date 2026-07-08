from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from monitoring.models import Patient, VitalReading, Alert
from datetime import datetime, timedelta
import random

class Command(BaseCommand):
    help = 'Generate sample patient data for testing'

    def handle(self, *args, **options):
        # Get or create doctor user
        doctor, _ = User.objects.get_or_create(
            username='doctor',
            defaults={
                'email': 'doctor@rgms.com',
                'first_name': 'John',
                'last_name': 'Doctor',
            }
        )
        if not doctor.password:
            doctor.set_password('password123')
            doctor.save()

        # Get or create Doctor group
        doctor_group, _ = Group.objects.get_or_create(name='Doctors')
        doctor.groups.add(doctor_group)

        # Get or create Caregiver user
        caregiver, _ = User.objects.get_or_create(
            username='caregiver',
            defaults={
                'email': 'caregiver@rgms.com',
                'first_name': 'Jane',
                'last_name': 'Caregiver',
            }
        )
        if not caregiver.password:
            caregiver.set_password('password123')
            caregiver.save()

        # Get or create Caregiver group
        caregiver_group, _ = Group.objects.get_or_create(name='Caregivers')
        caregiver.groups.add(caregiver_group)

        self.stdout.write('Creating sample patients...')
        
        # Create patients
        patients = []
        for i in range(1, 6):
            patient = Patient.objects.create(
                full_name=f'Patient {i}',
                email=f'patient{i}@rgms.com',
                gender=random.choice(['male', 'female']),
                phone_number=f'555-{i:04d}',
                care_type=random.choice(['in_patient', 'outpatient', 'home_care']),
                assigned_doctor=doctor,
                assigned_caregiver=caregiver,
            )
            patients.append(patient)
            self.stdout.write(f'  Created: {patient.full_name}')

        self.stdout.write('Creating vital readings...')
        
        # Store readings to use for alerts
        all_readings = []
        
        # Create vitals for the last 7 days
        for patient in patients:
            for day in range(7):
                date = datetime.now() - timedelta(days=day)
                for hour in [9, 12, 18]:  # Morning, noon, evening
                    reading = VitalReading.objects.create(
                        patient=patient,
                        systolic_bp=random.randint(110, 145),
                        diastolic_bp=random.randint(70, 92),
                        pulse_rate=random.randint(65, 85),
                        oxygen_saturation=random.randint(95, 100),
                        fasting_blood_sugar=random.randint(80, 125),
                        random_blood_sugar=random.randint(100, 155),
                        created_at=date.replace(hour=hour, minute=0, second=0, microsecond=0)
                    )
                    all_readings.append(reading)
            self.stdout.write(f'  Created readings for: {patient.full_name}')

        self.stdout.write('Creating sample alerts...')
        
        # Create some alerts using actual readings
        for i, reading in enumerate(all_readings[:10]):  # Use first 10 readings
            if i % 2 == 0:
                Alert.objects.create(
                    patient=reading.patient,
                    reading=reading,  # Link to the reading
                    title='Elevated Blood Pressure' if i % 4 == 0 else 'Low Oxygen Saturation',
                    severity=random.choice(['critical', 'warning']),
                    status='active',
                    message='Patient showing signs of hypertension. Monitor closely.' if i % 4 == 0 else 'Patient SpO2 levels below normal range.',
                )
                self.stdout.write(f'  Created alert for: {reading.patient.full_name}')

        self.stdout.write(self.style.SUCCESS('\n✅ Sample data generated successfully!'))
        self.stdout.write(self.style.SUCCESS(f'📊 {len(patients)} patients created'))
        self.stdout.write(self.style.SUCCESS(f'📈 {len(all_readings)} vital readings created'))
        self.stdout.write(self.style.SUCCESS(f'⚠️ {len(all_readings[:10])} alerts created'))
        self.stdout.write('\nLogin credentials:')
        self.stdout.write(f'  Doctor - Username: doctor, Password: password123')
        self.stdout.write(f'  Caregiver - Username: caregiver, Password: password123')