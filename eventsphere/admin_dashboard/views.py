from django.shortcuts import render
from django.contrib.auth.models import User
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
from django.contrib.admin.views.decorators import staff_member_required
from events.models import Event, RSVP

@staff_member_required
def admin_dashboard(request):
    today = timezone.localdate()

    total_users = User.objects.count()
    active_events = Event.objects.filter(date__gte=today, approval_status=Event.STATUS_APPROVED).count()
    total_rsvps = RSVP.objects.count()
    engaged_users = RSVP.objects.values('attendee').distinct().count()

    engagement_rate = round((engaged_users / total_users) * 100, 2) if total_users else 0

    events_by_city = (
    Event.objects.values('city')
        .annotate(event_count=Count('id'))
        .order_by('-event_count')
    )

    rsvps_by_city = (
        RSVP.objects.values('event__city')
        .annotate(rsvp_count=Count('id'))
        .order_by('-rsvp_count')
    )

    recent_users = User.objects.filter(date_joined__gte=timezone.now() - timedelta(days=30)).count()
    recent_events = Event.objects.filter(created_at__gte=timezone.now() - timedelta(days=30)).count()

    context = {
        'total_users': total_users,
        'active_events': active_events,
        'total_rsvps': total_rsvps,
        'engagement_rate': engagement_rate,
        'events_by_city': events_by_city,
        'rsvps_by_city': rsvps_by_city,
        'recent_users': recent_users,
        'recent_events': recent_events,
    }
    return render(request, 'admin_dashboard/dashboard.html', context)
