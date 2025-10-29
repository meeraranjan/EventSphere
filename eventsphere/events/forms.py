from django import forms
from .models import EventOrganizer

class EventOrganizerForm(forms.ModelForm):
    class Meta:
        model = EventOrganizer
        fields = ['organization_name', 'contact_email', 'phone_number']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
