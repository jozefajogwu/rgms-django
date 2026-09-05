# monitoring/forms.py

from django import forms
from django.core.validators import MinValueValidator, MaxValueValidator
from .models import VitalReading, AlertAction


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
        self.fields['systolic_bp'].help_text = "Normal: 100-140 mmHg"
        self.fields['diastolic_bp'].help_text = "Normal: 60-80 mmHg"
        self.fields['pulse_rate'].help_text = "Normal: 60-100 bpm"
        self.fields['oxygen_saturation'].help_text = "Normal: 95-100%"
        self.fields['fasting_blood_sugar'].help_text = "Normal: 70-100 mg/dL"
        self.fields['random_blood_sugar'].help_text = "Normal: 70-140 mg/dL"
        
        # Add placeholders
        self.fields['systolic_bp'].widget.attrs['placeholder'] = 'e.g., 120 (100-140 normal)'
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


# ============================================
# ALERT ACTION FORMS - Clinical Documentation
# ============================================

class AlertActionForm(forms.ModelForm):
    """
    Full form for documenting clinical actions on patient alerts
    Used for detailed clinical documentation
    """
    
    class Meta:
        model = AlertAction
        fields = [
            'action_type',
            'description',
            'notes',
            'clinical_findings',
            'assessment',
            'plan',
            'follow_up_needed',
            'follow_up_date',
            'follow_up_notes',
        ]
        widgets = {
            'description': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Describe the action taken in detail...',
                'class': 'form-input'
            }),
            'notes': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Additional notes or observations...',
                'class': 'form-input'
            }),
            'clinical_findings': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Document clinical findings...',
                'class': 'form-input'
            }),
            'assessment': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Clinical assessment...',
                'class': 'form-input'
            }),
            'plan': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Recommended next steps or treatment plan...',
                'class': 'form-input'
            }),
            'follow_up_notes': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Follow-up notes...',
                'class': 'form-input'
            }),
            'follow_up_date': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-input'
            }),
        }
        labels = {
            'action_type': 'Action Type',
            'description': 'Description of Action',
            'notes': 'Additional Notes',
            'clinical_findings': 'Clinical Findings',
            'assessment': 'Assessment',
            'plan': 'Plan / Recommendations',
            'follow_up_needed': 'Follow-up Needed',
            'follow_up_date': 'Follow-up Date & Time',
            'follow_up_notes': 'Follow-up Notes',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make description and action_type required
        self.fields['action_type'].required = True
        self.fields['description'].required = True
        
        # Add help texts
        self.fields['action_type'].help_text = "Select the type of action taken"
        self.fields['description'].help_text = "Provide a clear description of what was done"
        self.fields['clinical_findings'].help_text = "Document any clinical findings or observations"
        self.fields['assessment'].help_text = "Clinical assessment based on the findings"
        self.fields['plan'].help_text = "Recommended next steps or treatment plan"
        self.fields['follow_up_notes'].help_text = "Any additional notes for follow-up"
        
        # Add CSS classes for styling
        for field in self.fields:
            if hasattr(self.fields[field].widget, 'attrs'):
                if 'class' not in self.fields[field].widget.attrs:
                    self.fields[field].widget.attrs['class'] = 'form-input'
        
        # Special handling for checkbox
        self.fields['follow_up_needed'].widget.attrs['class'] = 'form-checkbox'
        self.fields['follow_up_needed'].widget.attrs['style'] = 'width: 20px; height: 20px; margin-right: 8px;'


class AlertActionSimpleForm(forms.ModelForm):
    """
    Simplified form for quick action documentation
    Used for quick actions from triage desk or live telemetry
    """
    
    class Meta:
        model = AlertAction
        fields = ['action_type', 'description', 'notes']
        widgets = {
            'description': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Describe action taken...',
                'class': 'form-input'
            }),
            'notes': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Additional notes...',
                'class': 'form-input'
            }),
        }
        labels = {
            'action_type': 'Action Type',
            'description': 'Description',
            'notes': 'Additional Notes',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make required fields
        self.fields['action_type'].required = True
        self.fields['description'].required = True
        
        # Add CSS classes
        for field in self.fields:
            if hasattr(self.fields[field].widget, 'attrs'):
                if 'class' not in self.fields[field].widget.attrs:
                    self.fields[field].widget.attrs['class'] = 'form-input'


class AlertQuickActionForm(forms.Form):
    """
    Quick action form for one-click actions from triage desk
    Used for simple actions like 'mark resolved' or 'acknowledge'
    """
    
    ACTION_CHOICES = [
        ('resolved', '✅ Mark as Resolved'),
        ('acknowledged', '👀 Acknowledge'),
        ('escalated', '🚨 Escalate'),
        ('monitored', '📊 Monitor'),
        ('contacted', '📞 Contact Patient'),
    ]
    
    action = forms.ChoiceField(choices=ACTION_CHOICES, widget=forms.Select(attrs={
        'class': 'form-input',
        'style': 'min-width: 180px;'
    }))
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 2,
            'placeholder': 'Quick notes (optional)...',
            'class': 'form-input'
        })
    )