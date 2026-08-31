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
from django.db.models import Sum, Max
from django.db.models.functions import TruncMonth
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from django.db.models.functions import TruncMonth, TruncDay


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







from django.db.models import Q

def account_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    context = {}
    profile_owner = request.user

    # Base queryset
    transactions_qs = Transaction.objects.filter(user=request.user).order_by('-transaction_date')

    # ---- Filters ----
    year = request.GET.get('year')
    month = request.GET.get('month')
    q = request.GET.get('q', '').strip()
    income = request.GET.get('income')
    expense = request.GET.get('expense')
    amount_min = request.GET.get('amount_min')
    amount_max = request.GET.get('amount_max')

    if year and year.isdigit():
        transactions_qs = transactions_qs.filter(transaction_date__year=year)
    if month and month.isdigit():
        transactions_qs = transactions_qs.filter(transaction_date__month=month)
    if q:
        transactions_qs = transactions_qs.filter(
            Q(transaction_name__icontains=q) |
            Q(transaction_type__icontains=q)
        )
    # Income/Expense filters
    if income and not expense:
        transactions_qs = transactions_qs.filter(transaction_ammount__gt=0)
    elif expense and not income:
        transactions_qs = transactions_qs.filter(transaction_ammount__lt=0)
    
    # Amount range
    if amount_min and amount_min.lstrip('-').isdigit():
        transactions_qs = transactions_qs.filter(transaction_ammount__gte=int(amount_min))
    if amount_max and amount_max.lstrip('-').isdigit():
        transactions_qs = transactions_qs.filter(transaction_ammount__lte=int(amount_max))

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


    # ---- Chart data ----
    # 1. Compute cumulative monthly balances from ALL transactions (unfiltered)
    all_transactions_qs = Transaction.objects.filter(user=request.user).order_by('transaction_date')
    monthly_agg_all = (all_transactions_qs
                    .annotate(month=TruncMonth('transaction_date'))
                    .values('month')
                    .annotate(balance=Sum('transaction_ammount'))
                    .order_by('month'))

    cumulative = 0
    all_monthly_cumulative = []
    for item in monthly_agg_all:
        cumulative += item['balance']
        all_monthly_cumulative.append({
            'month': item['month'],
            'cumulative': cumulative,
        })

    # 2. Decide chart data based on filters
    chart_data = {'labels': [], 'balances': []}

    # Check if a specific month is selected
    month_selected = month and month.isdigit()

    if month_selected:
        # Show daily net balances for that month (from filtered queryset)
        daily_agg = (transactions_qs
                    .annotate(day=TruncDay('transaction_date'))
                    .values('day')
                    .annotate(net=Sum('transaction_ammount'))
                    .order_by('day'))

        # Compute cumulative daily balance so the cart shows the running total for that month
        day_cumulative = 0
        daily_agg_cumulative = []
        for item in daily_agg:
            day_cumulative += item['net']
            daily_agg_cumulative.append({
                'day': item['day'],
                'cumulative': day_cumulative,
            })

        chart_data['labels'] = [item['day'].strftime('%b %d') for item in daily_agg_cumulative]
        chart_data['balances'] = [item['cumulative'] for item in daily_agg_cumulative]
    else:
        # Show cumulative monthly balances (filtered by year if selected)
        filtered_months = all_monthly_cumulative
        if year and year.isdigit():
            filtered_months = [m for m in all_monthly_cumulative if m['month'].year == int(year)]
        chart_data['labels'] = [m['month'].strftime('%b %Y') for m in filtered_months]
        chart_data['balances'] = [m['cumulative'] for m in filtered_months]

    # # ---- Monthly balances (cumulative) for graph ----
    # monthly_balances = []
    # if transactions_qs.exists():
    #     # Aggregate by month (non-cumulative)
    #     monthly_agg = (transactions_qs
    #                 .annotate(month=TruncMonth('transaction_date'))
    #                 .values('month')
    #                 .annotate(balance=Sum('transaction_ammount'))
    #                 .order_by('month'))
    #     # Compute cumulative balance
    #     cumulative = 0
    #     for item in monthly_agg:
    #         cumulative += item['balance']
    #         monthly_balances.append({
    #             'month': item['month'].strftime('%b %Y'),
    #             'balance': cumulative,
    #         })


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
        'search_query': q,
        'income_checked': income == 'on',
        'expense_checked': expense == 'on',
        'amount_min': amount_min,
        'amount_max': amount_max,
        'year_choices': year_choices,
        'month_choices': month_choices,
        'base_url': base_url,
    })
    context['chart_data_json'] = json.dumps(chart_data)

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