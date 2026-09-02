from django.urls import path
from . import views

app_name = 'dashboard'  # optional, for namespacing

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('categorisation/', views.categorisation_view, name='categorisation'),
    # add other dashboard URLs later (e.g., upload)
]