from django.contrib import admin

from .models import Profile, TipEntry


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'system_username', 'email', 'phone_number')
    search_fields = ('name', 'system_username', 'email')


@admin.register(TipEntry)
class TipEntryAdmin(admin.ModelAdmin):
    list_display = (
        'server',
        'service_date',
        'tips_made',
        'assistant_percent',
        'assistant_tipout',
        'bar_tipout',
        'total_tipout',
        'net_tips',
    )
    list_filter = ('service_date', 'assistant_percent')
    search_fields = ('server__username', 'server__first_name', 'server__last_name')
