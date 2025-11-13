# application/admin.py
from django.contrib import admin
from .models import Token, Place

# Register the Token model
@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = ('token', 'created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')

# Register the Place model
@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = ('place_id', 'name', 'lat', 'lng', 'created_at', 'updated_at')
    search_fields = ('name', 'address', 'place_id')
    list_filter = ('created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
