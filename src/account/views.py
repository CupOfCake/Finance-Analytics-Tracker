from django.shortcuts import render, redirect
from operator import attrgetter
from django.contrib.auth import login, authenticate, logout, get_user_model
from account.forms import AccountAuthenticationForm, RegistrationForm, AccountUpdateForm
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from finance.models import Transaction, TransactionSplit
from django.db.models import Sum, Prefetch
from django.shortcuts import render
import json
from django.db.models import Q

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

    # Base queryset
    transactions_qs = Transaction.objects.filter(user=request.user).order_by('transaction_date')

    # ---- Filters ----
    year = request.GET.get('year')
    month = request.GET.get('month')
    q = request.GET.get('q', '').strip()

    if year and year.isdigit():
        transactions_qs = transactions_qs.filter(transaction_date__year=year)
    if month and month.isdigit():
        transactions_qs = transactions_qs.filter(transaction_date__month=month)
    if q:
        transactions_qs = transactions_qs.filter(
            Q(transaction_name__icontains=q) |
            Q(transaction_type__icontains=q)
        )

    # Prefetch splits
    transactions_qs = transactions_qs.prefetch_related(
        Prefetch('splits', queryset=TransactionSplit.objects.select_related('user'))
    )

    # ---- Pagination ----
    paginator = Paginator(transactions_qs, 20)
    page = request.GET.get('page')
    try:
        transactions_page = paginator.page(page)
    except PageNotAnInteger:
        transactions_page = paginator.page(1)
    except EmptyPage:
        transactions_page = paginator.page(paginator.num_pages)

    # ---- Split data for current page ----
    transaction_splits_data = {}
    for txn in transactions_page:
        transaction_splits_data[str(txn.id)] = [
            {'user_id': s.user.id, 'username': s.user.username, 'amount': s.amount}
            for s in txn.splits.all()
        ]

    # ---- Global data ----
    all_users = User.objects.exclude(id=request.user.id).values('id', 'username')
    all_users_list = list(all_users)
    upload_results = request.session.pop('upload_results', None)
    has_transactions = Transaction.objects.filter(user=profile_owner).exists()

    # ---- Stats (filtered) ----
    total_income = transactions_qs.filter(transaction_ammount__gt=0).aggregate(Sum('transaction_ammount'))['transaction_ammount__sum'] or 0
    total_expense = transactions_qs.filter(transaction_ammount__lt=0).aggregate(Sum('transaction_ammount'))['transaction_ammount__sum'] or 0
    net_balance = total_income + total_expense
    transaction_count = transactions_qs.count()

    # ---- Year choices ----
    available_years = Transaction.objects.filter(user=request.user).dates('transaction_date', 'year', order='DESC')
    year_choices = [('', 'All years')] + [(str(year.year), str(year.year)) for year in available_years]

    # ---- Month choices ----
    month_choices = [
        ('', 'All months'),
        ('1', 'January'), ('2', 'February'), ('3', 'March'), ('4', 'April'),
        ('5', 'May'), ('6', 'June'), ('7', 'July'), ('8', 'August'),
        ('9', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December')
    ]

    # ---- Build base URL for pagination (preserve filters, remove page) ----
    get_params = request.GET.copy()
    get_params.pop('page', None)
    base_url = get_params.urlencode()
    if base_url:
        base_url = '?' + base_url + '&'
    else:
        base_url = '?'

    partner = request.user.partner
    context.update({
        'partner_id': partner.id if partner else None,
        'partner_username': partner.username if partner else None,
        'profile_owner': profile_owner,
        'transactions': transactions_page,
        'page_obj': transactions_page,
        'current_user_id': request.user.id,
        'current_user_name': request.user.username,
        'transaction_splits_json': transaction_splits_data,
        'all_users_json': all_users_list,
        'has_transactions': has_transactions,
        'upload_results': upload_results,
        'total_income': total_income,
        'total_expense': abs(total_expense),
        'net_balance': net_balance,
        'transaction_count': transaction_count,
        'selected_year': year,
        'selected_month': month,
        'year_choices': year_choices,
        'month_choices': month_choices,
        'search_query': q,
        'base_url': base_url,
    })

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