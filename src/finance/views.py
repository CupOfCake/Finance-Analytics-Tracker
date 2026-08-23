from django.shortcuts import render

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
