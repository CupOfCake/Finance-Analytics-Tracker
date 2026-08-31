from django import forms

class UploadTransactionsForm(forms.Form):
    file = forms.FileField(
        label='Select Excel file (.xlsx)',
        widget=forms.FileInput(attrs={'accept': '.xlsx'})
    )

class TransactionDeleteForm(forms.Form):
    transaction_pk = forms.IntegerField(widget=forms.HiddenInput)