from django.shortcuts import render, redirect

def dashboard_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    context = {}
    profile_owner = request.user

    context.update({
        'profile_owner': profile_owner,
    })

    return render(request, 'dashboard/dashboard.html', context)


def categorisation_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    context = {}
    profile_owner = request.user

    context.update({
        'profile_owner': profile_owner,
    })

    return render(request, 'dashboard/categorisation.html', context)