from django.urls import path
from . import views
from .views import (
    conversation_list,
    start_conversation,
    view_conversation,
    add_to_group,
    update_nickname
)

urlpatterns = [
    path("", conversation_list, name="conversation_list"),
    path("start/", start_conversation, name="start_conversation"),
    path("group/create/", views.create_group_chat, name="create_group_chat"),
    path("<int:conversation_id>/", views.view_conversation, name="view_conversation"),
    path("<int:conversation_id>/add/", views.add_to_group, name="add_to_group"),
    path('rename/<int:conversation_id>/', views.rename_group, name='rename_group'),
    path("<int:conversation_id>/nickname/", update_nickname, name="update_nickname"),

]
