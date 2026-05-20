from django import forms
from .models import VitalReading


class VitalReadingForm(forms.ModelForm):
    class Meta:
        model = VitalReading
        fields = [
            'patient',
            'fasting_blood_sugar',
            'random_blood_sugar',
            'systolic_bp',
            'diastolic_bp',
            'pulse_rate',
            'oxygen_saturation',
            
             'urine_glucose',
             'urine_protein',
             'urine_acetone',
             'urine_bilirubin',
             'urine_urobilinogen',
             'urine_nitrite',
            
            'symptoms',
            'notes',
        ]

        widgets = {
            'patient': forms.Select(attrs={
                'class': 'w-full rounded-lg border border-gray-300 px-4 py-3 text-lg focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),
            'fasting_blood_sugar': forms.NumberInput(attrs={
                'class': 'w-full rounded-lg border border-gray-300 px-4 py-3 text-lg focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Example: 95'
            }),
            'random_blood_sugar': forms.NumberInput(attrs={
                'class': 'w-full rounded-lg border border-gray-300 px-4 py-3 text-lg focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Example: 140'
            }),
            'systolic_bp': forms.NumberInput(attrs={
                'class': 'w-full rounded-lg border border-gray-300 px-4 py-3 text-lg focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Example: 120'
            }),
            'diastolic_bp': forms.NumberInput(attrs={
                'class': 'w-full rounded-lg border border-gray-300 px-4 py-3 text-lg focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Example: 80'
            }),
            'pulse_rate': forms.NumberInput(attrs={
                'class': 'w-full rounded-lg border border-gray-300 px-4 py-3 text-lg focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Example: 75'
            }),
            'oxygen_saturation': forms.NumberInput(attrs={
                 'class': 'w-full rounded-lg border border-gray-300 px-4 py-3 text-lg focus:outline-none focus:ring-2 focus:ring-blue-500',
                 'placeholder': 'Example: 98'
            }),
            
            'urine_glucose': forms.Select(attrs={
                 'class': 'w-full rounded-lg border border-gray-300 px-4 py-3 text-lg focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),

            'urine_protein': forms.Select(attrs={
                  'class': 'w-full rounded-lg border border-gray-300 px-4 py-3 text-lg focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),

            'urine_acetone': forms.Select(attrs={
                  'class': 'w-full rounded-lg border border-gray-300 px-4 py-3 text-lg focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),

            'urine_bilirubin': forms.Select(attrs={
                  'class': 'w-full rounded-lg border border-gray-300 px-4 py-3 text-lg focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),

            'urine_urobilinogen': forms.Select(attrs={
                    'class': 'w-full rounded-lg border border-gray-300 px-4 py-3 text-lg focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),

            'urine_nitrite': forms.Select(attrs={
                    'class': 'w-full rounded-lg border border-gray-300 px-4 py-3 text-lg focus:outline-none focus:ring-2 focus:ring-blue-500'
    }),
            
            
            'symptoms': forms.Textarea(attrs={
                'class': 'w-full rounded-lg border border-gray-300 px-4 py-3 text-lg focus:outline-none focus:ring-2 focus:ring-blue-500',
                'rows': 4,
                'placeholder': 'Enter symptoms if any'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'w-full rounded-lg border border-gray-300 px-4 py-3 text-lg focus:outline-none focus:ring-2 focus:ring-blue-500',
                'rows': 4,
                'placeholder': 'Additional notes'
            }),
        }