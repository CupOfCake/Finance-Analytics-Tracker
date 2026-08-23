from django.urls import path
from . import views

app_name = 'finance'  # optional, for namespacing

urlpatterns = [
    path('api/update-splits/<int:transaction_id>/', views.update_transaction_splits, name='update_splits'),
    # add other finance URLs later (e.g., upload)
]