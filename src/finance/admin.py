from django.contrib import admin

from finance.models import Transaction

class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'transaction_id',
        'transaction_date',
        'date_published',
        'date_updated',
    )
    
    search_fields = (
        'user__email',          # search by user's email
        'user__username',       # search by user's username
        'transaction_id',       # search by transaction reference
        'transaction_name',     # search by transaction description
    )
    
    list_filter = (
        'user',
        'transaction_type',
        'transaction_date',
    )
    
    readonly_fields = (
        'date_published',
        'date_updated',
    )
    
    ordering = ('-transaction_date',)   # show newest first

admin.site.register(Transaction, TransactionAdmin)
