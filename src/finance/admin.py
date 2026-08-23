from django.contrib import admin

from finance.models import Transaction, TransactionSplit

class TransactionSplitInline(admin.TabularInline):
    model = TransactionSplit
    extra = 1                      # one blank split form
    fields = ('user', 'amount')    # which fields to show

class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'transaction_id',
        'transaction_date',
        'transaction_ammount',
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

    inlines = [TransactionSplitInline]

admin.site.register(Transaction, TransactionAdmin)




class TransactionSplitAdmin(admin.ModelAdmin):
    list_display = ('transaction', 'user', 'amount')
    search_fields = ('transaction__transaction_name', 'user__username')
    list_filter = ('user',)

admin.site.register(TransactionSplit, TransactionSplitAdmin)