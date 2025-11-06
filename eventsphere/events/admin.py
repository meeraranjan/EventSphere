from django.contrib import admin
from .models import Event, EventOrganizer, RSVP

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "date", "time", "organizer","approval_status")
    list_filter = ("category", "date", "approval_status")
    search_fields = ("title", "description", "location")
    actions = ["approve_events", "reject_events"]
    @admin.action(description="Approve selected events")
    def approve_events(self, request, queryset):
        updated = queryset.update(approval_status="approved")
        self.message_user(request, f"{updated} event(s) approved.")

    @admin.action(description="Reject selected events")
    def reject_events(self, request, queryset):
        updated = queryset.update(approval_status="rejected")
        self.message_user(request, f"{updated} event(s) rejected.")
@admin.register(EventOrganizer)
class EventOrganizerAdmin(admin.ModelAdmin):
    list_display = ("organization_name", "contact_email", "phone_number")
    search_fields = ("organization_name", "profile__user__username")

@admin.register(RSVP)
class RSVPAdmin(admin.ModelAdmin):
    list_display = ("event", "attendee", "status", "contact_email", "created_at")
    list_filter = ("status", "created_at", "event")
    search_fields = ("attendee__username", "attendee__email", "event__title", "contact_email")