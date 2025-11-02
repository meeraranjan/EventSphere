from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import UserProfile

class SignUpForm(UserCreationForm):
    user_type = forms.ChoiceField(
        choices=UserProfile.USER_TYPE_CHOICES,
        widget=forms.RadioSelect,
        required=True,
        label="Sign up as"
    )
    organization_name = forms.CharField(
        max_length=255,
        required=False,
        label="Organization Name",
        help_text="Required for organizers"
    )
    age = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=150,
        label="Age",
        help_text="Required for attendees"
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'user_type', 'organization_name', 'age']

    def __init__(self, *args, **kwargs):
        super(SignUpForm, self).__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, forms.RadioSelect):
                field.widget.attrs.update({'class': 'form-control'})
    
    def clean(self):
        cleaned_data = super().clean()
        # No strict validation - backend will handle defaults
        return cleaned_data

