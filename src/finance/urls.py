from django.urls import path
from . import views

app_name = 'finance'  # optional, for namespacing

urlpatterns = [
    path('api/update-splits/<int:transaction_id>/', views.update_transaction_splits, name='update_splits'),
    path('upload/', views.upload_transactions, name='upload_transactions'),
    path('delete/<int:transaction_pk>/', views.delete_transaction, name='delete_transaction'),
    path('delete-filtered/', views.delete_filtered_transactions, name='delete_filtered_transactions'),
    # add other finance URLs later (e.g., upload)
]