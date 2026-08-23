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
                df = pd.read_excel(excel_file, engine='openpyxl')
                required_cols = ['Dagsetning', 'Innlend upphæð', 'Lýsing', 'Heimildarnúmer']
                if not all(col in df.columns for col in required_cols):
                    messages.error(request, f'Invalid file format. Expected columns: {", ".join(required_cols)}')
                    return redirect('account')

                created_count = 0
                skipped_count = 0

                for _, row in df.iterrows():
                    tID = row['Heimildarnúmer']
                    if pd.isna(tID):
                        continue

                    date_val = row['Dagsetning']
                    if isinstance(date_val, pd.Timestamp):
                        transaction_date = date_val.to_pydatetime()
                    else:
                        # fallback for string dates
                        transaction_date = pd.to_datetime(date_val).to_pydatetime()

                    # Make the datetime timezone-aware
                    transaction_date = make_aware(transaction_date)

                    amount = int(row['Innlend upphæð'])
                    description = str(row['Lýsing'])

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