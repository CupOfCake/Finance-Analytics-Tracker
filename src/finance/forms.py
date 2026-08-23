from django import forms

class UploadTransactionsForm(forms.Form):
    file = forms.FileField(
        label='Select Excel file (.xlsx)',
        widget=forms.FileInput(attrs={'accept': '.xlsx'})
    )