# monitoring/forms.py

from django import forms
from django.core.validators import MinValueValidator, MaxValueValidator
from .models import VitalReading


class VitalReadingForm(forms.ModelForm):
    """Form for adding vital readings with validation"""
    
    class Meta:
        model = VitalReading
        fields = [
            'patient', 'fasting_blood_sugar', 'random_blood_sugar',
            'systolic_bp', 'diastolic_bp', 'pulse_rate', 'oxygen_saturation',
            'urine_glucose', 'urine_protein', 'urine_acetone', 'urine_bilirubin',
            'urine_urobilinogen', 'urine_nitrite', 'symptoms', 'notes'
        ]
        widgets = {
            'symptoms': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Describe any symptoms...'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Any additional notes...'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add custom help texts and placeholders
        self.fields['systolic_bp'].help_text = "Normal: 90-120 mmHg"
        self.fields['diastolic_bp'].help_text = "Normal: 60-80 mmHg"
        self.fields['pulse_rate'].help_text = "Normal: 60-100 bpm"
        self.fields['oxygen_saturation'].help_text = "Normal: 95-100%"
        self.fields['fasting_blood_sugar'].help_text = "Normal: 70-100 mg/dL"
        self.fields['random_blood_sugar'].help_text = "Normal: 70-140 mg/dL"
        
        # Add placeholders
        self.fields['systolic_bp'].widget.attrs['placeholder'] = 'e.g., 120'
        self.fields['diastolic_bp'].widget.attrs['placeholder'] = 'e.g., 80'
        self.fields['pulse_rate'].widget.attrs['placeholder'] = 'e.g., 72'
        self.fields['oxygen_saturation'].widget.attrs['placeholder'] = 'e.g., 98'
        self.fields['fasting_blood_sugar'].widget.attrs['placeholder'] = 'e.g., 95'
        self.fields['random_blood_sugar'].widget.attrs['placeholder'] = 'e.g., 110'
    
    def clean_systolic_bp(self):
        value = self.cleaned_data.get('systolic_bp')
        if value > 300:
            raise forms.ValidationError('Systolic BP cannot exceed 300 mmHg. Please check your reading.')
        if value < 50:
            raise forms.ValidationError('Systolic BP cannot be below 50 mmHg. Please check your reading.')
        return value
    
    def clean_diastolic_bp(self):
        value = self.cleaned_data.get('diastolic_bp')
        if value > 200:
            raise forms.ValidationError('Diastolic BP cannot exceed 200 mmHg. Please check your reading.')
        if value < 30:
            raise forms.ValidationError('Diastolic BP cannot be below 30 mmHg. Please check your reading.')
        return value
    
    def clean_pulse_rate(self):
        value = self.cleaned_data.get('pulse_rate')
        if value > 250:
            raise forms.ValidationError('Pulse rate cannot exceed 250 bpm. Please check your reading.')
        if value < 30:
            raise forms.ValidationError('Pulse rate cannot be below 30 bpm. Please check your reading.')
        return value
    
    def clean_fasting_blood_sugar(self):
        value = self.cleaned_data.get('fasting_blood_sugar')
        if value and value > 1000:
            raise forms.ValidationError('Fasting blood sugar cannot exceed 1000 mg/dL. Please check your reading.')
        if value and value < 0:
            raise forms.ValidationError('Fasting blood sugar cannot be negative.')
        return value
    
    def clean_random_blood_sugar(self):
        value = self.cleaned_data.get('random_blood_sugar')
        if value and value > 1000:
            raise forms.ValidationError('Random blood sugar cannot exceed 1000 mg/dL. Please check your reading.')
        if value and value < 0:
            raise forms.ValidationError('Random blood sugar cannot be negative.')
        return value
    
    def clean_oxygen_saturation(self):
        value = self.cleaned_data.get('oxygen_saturation')
        if value:
            if value > 100:
                raise forms.ValidationError('SpO2 cannot exceed 100%. Please check your reading.')
            if value < 50:
                raise forms.ValidationError('SpO2 cannot be below 50%. Please check your reading.')
        return value