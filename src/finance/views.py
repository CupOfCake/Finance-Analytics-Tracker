from django.shortcuts import render

import pandas as pd
from django.shortcuts import redirect
from django.contrib import messages
from django.db import IntegrityError
from .forms import UploadTransactionsForm
from django.utils.timezone import make_aware
from django.conf import settings

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import Transaction, TransactionSplit
from django.contrib.auth import get_user_model

User = get_user_model()

@login_required
@csrf_exempt  # or use proper CSRF token in AJAX
def update_transaction_splits(request, transaction_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        transaction = Transaction.objects.get(pk=transaction_id, user=request.user)
    except Transaction.DoesNotExist:
        return JsonResponse({'error': 'Transaction not found'}, status=404)
    
    data = json.loads(request.body)
    splits_data = data.get('splits', [])
    
    # Validate sum
    total = sum(s['amount'] for s in splits_data)
    if total != transaction.transaction_ammount:
        return JsonResponse({'error': f'Sum of splits ({total}) must equal transaction amount ({transaction.transaction_ammount})'}, status=400)
    
    # Replace all splits
    transaction.splits.all().delete()
    for item in splits_data:
        user_id = item.get('user_id')
        amount = item.get('amount')
        if user_id is None or amount is None:
            continue
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            continue
        TransactionSplit.objects.create(
            transaction=transaction,
            user=user,
            amount=amount
        )
    
    return JsonResponse({'status': 'ok'})



@login_required
def upload_transactions(request):
    if request.method == 'POST':
        form = UploadTransactionsForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = request.FILES['file']
            if not excel_file.name.endswith('.xlsx'):
                messages.error(request, 'Please upload a .xlsx file.')
                return redirect('account')

            try:
                # Read the file without assuming header row first
                # Try header=0 (credit card format)
                df_credit = pd.read_excel(excel_file, engine='openpyxl', header=0)
                credit_cols = ['Dagsetning', 'Innlend upphæð', 'Lýsing', 'Heimildarnúmer']
                if all(col in df_credit.columns for col in credit_cols):
                    # Credit card format
                    df = df_credit
                    parser = 'credit'
                else:
                    # Try header=3 (debit/account format)
                    df_debit = pd.read_excel(excel_file, engine='openpyxl', header=3)
                    debit_cols = ['Dagsetning', 'Upphæð', 'Skýring', 'Texti', 'Einkvæmur lykill', 'Nafn viðtakanda eða greiðanda']
                    if all(col in df_debit.columns for col in debit_cols):
                        df = df_debit
                        parser = 'debit'
                    else:
                        messages.error(request, 'Unrecognized file format. Expected Arion credit card or debit/account export.')
                        return redirect('account')

                created_count = 0
                skipped_count = 0

                if parser == 'credit':
                    for _, row in df.iterrows():
                        tID = row['Heimildarnúmer']
                        description = str(row['Lýsing']) if not pd.isna(row['Lýsing']) else ''

                        # Special handling for Útskriftargjald (statement fee)
                        if pd.isna(tID) and 'Útskriftargjald' in description:
                            # Use a dummy transaction_id (e.g., -1)
                            # To avoid conflicts if multiple such fees on the same date, we can use -1 - month? but date is different, so -1 is fine.
                            tID = -1

                        if pd.isna(tID):
                            continue  # skip other rows without a valid ID

                        date_val = row['Dagsetning']
                        if isinstance(date_val, pd.Timestamp):
                            transaction_date = date_val.to_pydatetime()
                        else:
                            transaction_date = pd.to_datetime(date_val).to_pydatetime()
                        transaction_date = make_aware(transaction_date)

                        amount = int(row['Innlend upphæð'])

                        if ' - ' in description:
                            parts = description.rsplit(' - ', 1)
                            transaction_type = parts[1].strip()
                            transaction_name = parts[0].strip()
                        else:
                            transaction_type = 'Unknown'
                            transaction_name = description

                        try:
                            Transaction.objects.create(
                                user=request.user,
                                transaction_id=int(tID),
                                transaction_date=transaction_date,
                                transaction_ammount=amount,
                                transaction_name=transaction_name,
                                transaction_type=transaction_type,
                            )
                            created_count += 1
                        except IntegrityError:
                            skipped_count += 1

                else:  # debit
                    username = request.user.username
                    for _, row in df.iterrows():
                        tID = row['Einkvæmur lykill']
                        if pd.isna(tID):
                            continue

                        date_val = row['Dagsetning']
                        if isinstance(date_val, pd.Timestamp):
                            transaction_date = date_val.to_pydatetime()
                        else:
                            transaction_date = pd.to_datetime(date_val).to_pydatetime()
                        transaction_date = make_aware(transaction_date)

                        amount = int(row['Upphæð'])
                        description = str(row['Skýring']) if not pd.isna(row['Skýring']) else ''
                        counterparty = str(row['Nafn viðtakanda eða greiðanda']) if not pd.isna(row['Nafn viðtakanda eða greiðanda']) else ''
                        transaction_type = str(row['Texti']) if not pd.isna(row['Texti']) else ''

                        # Skip if "Arion banki hf." appears in description or counterparty
                        if 'arion banki hf.' in description.lower() or 'arion banki hf.' in counterparty.lower():
                            continue

                        # Skip if both description and counterparty contain the username
                        if description and counterparty:
                            if username.lower() in description.lower() and username.lower() in counterparty.lower():
                                continue

                        # Build transaction name
                        if counterparty:
                            transaction_name = f"{description} - {counterparty}" if description else counterparty
                        else:
                            transaction_name = description or 'Unknown'

                        try:
                            Transaction.objects.create(
                                user=request.user,
                                transaction_id=int(tID),
                                transaction_date=transaction_date,
                                transaction_ammount=amount,
                                transaction_name=transaction_name,
                                transaction_type=transaction_type,
                            )
                            created_count += 1
                        except IntegrityError:
                            skipped_count += 1

                request.session['upload_results'] = {
                    'created': created_count,
                    'skipped': skipped_count
                }
                messages.success(
                    request,
                    f'Successfully added {created_count} transactions. '
                    f'Skipped {skipped_count} duplicate(s).'
                )

            except Exception as e:
                messages.error(request, f'Error processing file: {e}')

        else:
            messages.error(request, 'Invalid form submission.')

        return redirect('account')

    return redirect('account')