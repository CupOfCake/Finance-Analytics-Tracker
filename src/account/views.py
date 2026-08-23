from django.shortcuts import render, redirect
from operator import attrgetter
from django.contrib.auth import login, authenticate, logout, get_user_model
from account.forms import AccountAuthenticationForm, RegistrationForm, AccountUpdateForm
from finance.models import Transaction, TransactionSplit
from django.db.models import Sum, Prefetch
from django.shortcuts import render
import json

User = get_user_model()


def registration_view(request):
    
    context = {}

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            email = form.cleaned_data.get('email')
            raw_password = form.cleaned_data.get('password1')
            account = authenticate(email=email, password=raw_password)
            login(request, account)
            return redirect('home')
        else:
            context['registration_form'] = form
    else: # GET request
        form = RegistrationForm()
        context['registration_form'] = form

    return render(request, 'account/register.html', context)


def logout_view(request):
    logout(request)
    return redirect('home')



def login_view(request):
    context = {}

    user = request.user
    if user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = AccountAuthenticationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = authenticate(email=email, password=password)

            if user:
                login(request, user)
                return redirect('home')
        
    else: # GET request
        form = AccountAuthenticationForm()

    context['login_form'] = form
    render(request, 'account/login.html', context)

    return render(request, 'account/login.html', context)



def account_view(request):

    if not request.user.is_authenticated:
        return redirect('login')
    
    context = {}

    profile_owner = request.user

    transactions = (Transaction.objects
                    .filter(user=request.user)
                    .order_by('transaction_date') #db sort
                    .prefetch_related(
                        Prefetch('splits',
                                 queryset=TransactionSplit.objects.select_related('user'))
                    ))

    # Build splits data (as a Python dict of lists)
    transaction_splits_data = {}
    for txn in transactions:
        transaction_splits_data[str(txn.id)] = [
            {'user_id': s.user.id, 'username': s.user.username, 'amount': s.amount}
            for s in txn.splits.all()
        ]

    # Get all users except the owner (as a list of dicts)
    all_users = User.objects.exclude(id=request.user.id).values('id', 'username')
    all_users_list = list(all_users)   # already a list of dicts


    partner = request.user.partner
    context['partner_id'] = partner.id if partner else None
    context['partner_username'] = partner.username if partner else None
    context['profile_owner'] = profile_owner
    context['transactions'] = transactions
    context['current_user_id'] = request.user.id
    context['current_user_name'] = request.user.username
    context['transaction_splits_json'] = transaction_splits_data
    context['all_users_json'] = all_users_list

    return render(request, 'account/account.html', context)




def account_update_view(request):
    if not request.user.is_authenticated:
        return redirect('login')

    context = {}

    if request.POST:
        form = AccountUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            context['success_message'] = "Updated"
            form = AccountUpdateForm(instance=request.user)
    else:
        form = AccountUpdateForm(
            initial={
                'email': request.user.email,
                'username': request.user.username,
                'partner': request.user.partner,
            }
        )

    # All users except the current one (for partner dropdown)
    all_users = User.objects.exclude(id=request.user.id).values('id', 'username')
    context['all_users'] = list(all_users)
    context['account_form'] = form

    return render(request, 'account/account_update.html', context)