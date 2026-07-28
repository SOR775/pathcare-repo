from django import forms
from django.contrib.auth import get_user_model

from .models import Carrier, CarrierIssue, CarrierIssueReply, Client, Order, Sample
from core.models import Facility

User = get_user_model()


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ["name", "contact_name", "contact_phone", "contact_email", "address"]


class CarrierForm(forms.Form):
    """Creates both the underlying User and the Carrier profile in one form."""

    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    phone = forms.CharField(max_length=32)
    vehicle_type = forms.CharField(max_length=64, required=False)
    vehicle_plate = forms.CharField(max_length=32, required=False)

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("That username is already taken.")
        return username

    def save(self):
        user = User.objects.create_user(
            username=self.cleaned_data["username"],
            password=self.cleaned_data["password"],
            first_name=self.cleaned_data.get("first_name", ""),
            last_name=self.cleaned_data.get("last_name", ""),
        )
        return Carrier.objects.create(
            user=user,
            phone=self.cleaned_data["phone"],
            vehicle_type=self.cleaned_data.get("vehicle_type", ""),
            vehicle_plate=self.cleaned_data.get("vehicle_plate", ""),
        )


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["client", "priority", "requested_pickup_time", "notes"]
        widgets = {
            "requested_pickup_time": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class SearchableSelect(forms.Select):
    """Custom select widget that adds search/filter functionality."""
    def __init__(self, attrs=None):
        super().__init__(attrs)
        self.attrs['class'] = 'searchable-select'
        self.attrs['data-searchable'] = 'true'


class ClientPickupRequestForm(forms.Form):
    facility = forms.ModelChoiceField(
        queryset=Facility.objects.filter(is_active=True).order_by("name"),
        label="Pickup Facility",
        empty_label="Search and select a facility",
        help_text="Start typing to search for a facility",
        widget=SearchableSelect(attrs={
            'placeholder': 'Search facility...',
            'class': 'form-control searchable-select',
        })
    )
    pickup_address = forms.CharField(
        required=False,
        label="Physical Address",
        widget=forms.TextInput(attrs={"readonly": "readonly"}),
    )
    latitude = forms.FloatField(required=False, widget=forms.HiddenInput())
    longitude = forms.FloatField(required=False, widget=forms.HiddenInput())
    contact_person = forms.CharField(max_length=255)
    contact_phone = forms.CharField(max_length=32)
    requested_pickup_time = forms.DateTimeField(required=False, widget=forms.DateTimeInput(attrs={"type": "datetime-local"}))
    samples_ready_at = forms.DateTimeField(required=False, widget=forms.DateTimeInput(attrs={"type": "datetime-local"}))
    reception_details = forms.CharField(required=False, max_length=255)
    parking_notes = forms.CharField(required=False, max_length=255)
    security_instructions = forms.CharField(required=False, max_length=255)
    priority = forms.ChoiceField(choices=Order.Priority.choices)
    temperature_requirement = forms.ChoiceField(label="Temperature requirement", choices=Sample.ColdChain.choices)
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))


class SampleForm(forms.ModelForm):
    class Meta:
        model = Sample
        fields = ["barcode", "sample_type", "cold_chain_requirement", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 2})}


class CarrierIssueForm(forms.ModelForm):
    class Meta:
        model = CarrierIssue
        fields = ["category", "description", "order"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "order": forms.HiddenInput(),
        }
        labels = {
            "category": "Issue type",
            "description": "Issue details",
        }


class CarrierIssueReplyForm(forms.ModelForm):
    class Meta:
        model = CarrierIssueReply
        fields = ["message"]
        widgets = {
            "message": forms.Textarea(attrs={"rows": 4, "placeholder": "Write your response..."}),
        }
        labels = {
            "message": "Reply",
        }


class AssignCarrierForm(forms.Form):
    carrier = forms.ModelChoiceField(queryset=Carrier.objects.none(), empty_label="Select a carrier")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        active_statuses = Order.active_statuses()
        self.fields["carrier"].queryset = (
            Carrier.objects.filter(is_active=True, status=Carrier.Status.AVAILABLE)
            .exclude(orders__status__in=active_statuses)
            .distinct()
        )


class FacilityForm(forms.ModelForm):
    class Meta:
        model = Facility
        fields = ["name", "address", "latitude", "longitude", "contact_name", "contact_phone", "contact_email", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.TextInput(attrs={"class": "form-control"}),
            "latitude": forms.NumberInput(attrs={"class": "form-control", "step": "0.00001"}),
            "longitude": forms.NumberInput(attrs={"class": "form-control", "step": "0.00001"}),
            "contact_name": forms.TextInput(attrs={"class": "form-control"}),
            "contact_phone": forms.TextInput(attrs={"class": "form-control"}),
            "contact_email": forms.EmailInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }