from django.shortcuts import render, redirect

from account.models import Account

# Create your views here.

def home_screen_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard/dashboard') #if the user is logged in we serve the dashboard, else just a basic landing page to sign in.

    context = {}

    accounts = Account.objects.all()
    context['accounts'] = accounts

    return render(request, 'core/home.html', context)