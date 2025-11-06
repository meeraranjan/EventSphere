from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.shortcuts import redirect

# Add a title with dashboard link
admin.site.site_header = "EventSphere Admin"
admin.site.site_title = "EventSphere Admin"
admin.site.index_title = format_html(
    'Welcome to EventSphere Admin | <a href="{}">📊 View Dashboard</a>',
    reverse('admin_dashboard')
)
