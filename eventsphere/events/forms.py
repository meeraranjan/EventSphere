from django import forms
from .models import EventOrganizer, Event

class EventOrganizerForm(forms.ModelForm):
    class Meta:
        model = EventOrganizer
        fields = ['organization_name', 'contact_email', 'phone_number']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            'title', 'description', 'location',
            'latitude', 'longitude', 'date', 'time',
            'price', 'ticket_url', 'capacity', 'image',
            'category',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'ticket_url': forms.URLInput(attrs={'class': 'form-control'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
        }

class EventFilterForm(forms.Form):
    category = forms.ChoiceField(
        choices=[('', 'All categories')] + list(Event.CATEGORY_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    radius = forms.FloatField(
            required=False,
            label="Radius (km)",
            widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter radius in km'})
        )
    user_lat = forms.FloatField(widget=forms.HiddenInput(), required=False)
    user_lng = forms.FloatField(widget=forms.HiddenInput(), required=False)
    def clean(self):
        data = super().clean()
        sd, ed = data.get('start_date'), data.get('end_date')
        if sd and ed and sd > ed:
            self.add_error('end_date', 'End date must be on or after start date.')
        return data