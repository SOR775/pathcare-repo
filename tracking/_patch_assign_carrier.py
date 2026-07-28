from pathlib import Path
path = Path('tracking/forms.py')
text = path.read_text()
old = '''class AssignCarrierForm(forms.Form):
    carrier = forms.ModelChoiceField(
        queryset=Carrier.objects.filter(is_active=True, status=Carrier.Status.AVAILABLE),
        empty_label="Select a carrier",
    )'''
new = '''class AssignCarrierForm(forms.Form):
    carrier = forms.ModelChoiceField(queryset=Carrier.objects.none(), empty_label="Select a carrier")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        active_statuses = Order.active_statuses()
        self.fields["carrier"].queryset = (
            Carrier.objects.filter(is_active=True, status=Carrier.Status.AVAILABLE)
            .exclude(orders__status__in=active_statuses)
            .distinct()
        )'''
if old not in text:
    raise RuntimeError('Old AssignCarrierForm block not found in forms.py')
path.write_text(text.replace(old, new, 1))
print('patched AssignCarrierForm')
