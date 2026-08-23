from django.shortcuts import render, redirect
from operator import attrgetter
from django.contrib.auth import login, authenticate, logout
from account.forms import AccountAuthenticationForm, RegistrationForm, AccountUpdateForm
from finance.models import Transaction


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

    transactions = sorted(Transaction.objects.filter(user=request.user),key=attrgetter('transaction_date'), reverse=False)

    context['profile_owner'] = profile_owner
    context['transactions'] = transactions
    return render(request, 'account/account.html', context)




def account_update_view(request):

    if not request.user.is_authenticated:
        return redirect('login')
    
    context: dict[str,object] = {}

    if request.POST:
        form = AccountUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.initial = {
                'profile_pic': form.cleaned_data['profile_pic'],
                'email': form.cleaned_data['email'],
                'username': form.cleaned_data['username'],
            }
            form.save()
            context['success_message'] = "Updated"

    else: # GET request
        form = AccountUpdateForm(
            initial={
                'email': request.user.email,
                'username': request.user.username,
            }
        )

    context['account_form'] = form
    return render(request, 'account/account_update.html', context)