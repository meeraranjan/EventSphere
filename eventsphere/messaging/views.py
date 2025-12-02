from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import Conversation, Message, ConversationNickname, MessageRead
from django.db import models

@login_required
def start_conversation(request):
    if request.method == "POST":
        raw = request.POST.get("usernames", "").strip()

        # Parse usernames
        username_list = [u.strip() for u in raw.split(",") if u.strip()]
        username_list = list(set(username_list))  # remove duplicates

        if len(username_list) == 0:
            return render(request, "messaging/start_chat.html", {
                "error": "Please enter at least one username."
            })

        # Fetch users
        users = list(User.objects.filter(username__in=username_list))

        # Check for invalid names
        if len(users) != len(username_list):
            return render(request, "messaging/start_chat.html", {
                "error": "One or more usernames were not found."
            })

        # Prevent adding yourself
        if request.user.username in username_list:
            return render(request, "messaging/start_chat.html", {
                "error": "You cannot start a conversation with yourself."
            })

        # ======================================
        # 1-ON-1 CHAT LOGIC
        # ======================================
        if len(users) == 1:
            friend = users[0]

            # Check if a 1-on-1 conversation already exists
            existing = Conversation.objects.filter(participants=request.user)\
                                           .filter(participants=friend)

            for convo in existing:
                if convo.participants.count() == 2:
                    return redirect("view_conversation", conversation_id=convo.id)

            # Create new 1-on-1 convo
            convo = Conversation.objects.create()
            convo.participants.add(request.user, friend)
            return redirect("view_conversation", conversation_id=convo.id)

        # ======================================
        # GROUP CHAT LOGIC
        # ======================================
        convo = Conversation.objects.create()
        convo.participants.add(request.user)
        convo.participants.add(*users)

        return redirect("view_conversation", conversation_id=convo.id)

    return render(request, "messaging/start_chat.html")

@login_required
def create_group_chat(request):
    if request.method == "POST":
        usernames = request.POST.get("usernames").split(",")  # comma-separated usernames
        users = User.objects.filter(username__in=[u.strip() for u in usernames])

        # Create group conversation
        convo = Conversation.objects.create(
            name=request.POST.get("name") or None
        )
        convo.participants.add(request.user)
        convo.participants.add(*users)

        return redirect("view_conversation", conversation_id=convo.id)

    return render(request, "messaging/create_group.html")

@login_required
def add_to_group(request, conversation_id):
    convo = get_object_or_404(Conversation, id=conversation_id)

    if request.method == "POST":
        username = request.POST.get("username")
        user = get_object_or_404(User, username=username)
        convo.participants.add(user)
        return redirect("view_conversation", conversation_id=convo.id)

    return render(request, "messaging/add_to_group.html", {"conversation": convo})

@login_required
def conversation_list(request):
    # Only show conversations with at least one message
    conversations = (
        Conversation.objects
        .filter(participants=request.user, messages__isnull=False)
        .distinct()
        .order_by('-created_at')
    )

    formatted = []

    for convo in conversations:
        if not convo.id:
            continue

        # --- Nicknames for this conversation ---
        nick_qs = ConversationNickname.objects.filter(conversation=convo)
        nickname_map = {n.user_id: n.nickname for n in nick_qs}

        def display_name(user):
            return nickname_map.get(user.id, user.username)

        # Other users
        others_qs = convo.participants.exclude(id=request.user.id)
        other_names = [display_name(u) for u in others_qs]

        # Latest message (we know at least 1 exists)
        latest = convo.messages.order_by("-timestamp").first()
        if not latest:
            continue

        latest_sender = display_name(latest.sender)
        latest_text = latest.text
        latest_time = latest.timestamp

        # --- UNREAD COUNT: only messages from others, not yet read ---
        unread_count = convo.messages.exclude(
            reads__user=request.user
        ).exclude(
            sender=request.user
        ).count()

        formatted.append({
            "convo": convo,
            "others": other_names,
            "latest_sender": latest_sender,
            "latest_text": latest_text,
            "latest_time": latest_time,
            "unread_count": unread_count,
        })

    return render(request, "messaging/conversations_list.html", {
        "conversations": formatted
    })

@login_required
def view_conversation(request, conversation_id, add_member_error=None):
    conversation = get_object_or_404(Conversation, id=conversation_id)

    # Ensure the user is part of the conversation
    if request.user not in conversation.participants.all():
        return redirect("conversation_list")

    # All messages
    chat_messages = conversation.messages.order_by("timestamp")

    # Mark unread messages as read
    unread_messages = chat_messages.exclude(
        reads__user=request.user
    ).exclude(
        sender=request.user
    )
    for msg in unread_messages:
        MessageRead.objects.get_or_create(message=msg, user=request.user)

    # Other users in the convo
    other_participants = conversation.participants.exclude(id=request.user.id)

    # Nicknames for this conversation
    nick_qs = ConversationNickname.objects.filter(conversation=conversation)
    nickname_map = {cn.user_id: cn.nickname for cn in nick_qs}

    def display_name(user):
        return nickname_map.get(user.id, user.username)

    # Sidebar participants list
    participants_display = [
        {
            "user": p,
            "name": display_name(p),
            "is_me": (p.id == request.user.id),
        }
        for p in conversation.participants.all()
    ]

    # Names for header
    others_display = [display_name(p) for p in other_participants]

    # Messages for display
    messages_display = [
        {
            "msg": msg,
            "name": display_name(msg.sender),
            "is_me": (msg.sender_id == request.user.id),
        }
        for msg in chat_messages
    ]

    # 🚨 IMPORTANT FIX:
    # If add_member_error is present, DO NOT process message POST.
    # This prevents the redirect that would block the modal.
    if not add_member_error:
        if request.method == "POST":
            text = request.POST.get("text", "").strip()
            if text:
                Message.objects.create(
                    conversation=conversation,
                    sender=request.user,
                    text=text
                )
            return redirect("view_conversation", conversation_id=conversation.id)

    # Render full chat view with the optional error
    return render(request, "messaging/chat.html", {
        "conversation": conversation,
        "chat_messages": chat_messages,
        "messages_display": messages_display,
        "participants_display": participants_display,
        "others_display": others_display,
        "self_display_name": display_name(request.user),
        "other_participants": other_participants,

        "add_member_error": add_member_error,
        "nickname_map": nickname_map,
    })

@login_required
def rename_group(request, conversation_id):
    convo = get_object_or_404(Conversation, id=conversation_id)

    # Only allow renaming if it's a group
    if convo.participants.count() <= 2:
        return redirect("view_conversation", conversation_id=convo.id)

    # Must be a member
    if request.user not in convo.participants.all():
        return redirect("conversation_list")

    if request.method == "POST":
        new_name = request.POST.get("name", "").strip()
        if new_name:
            convo.name = new_name
            convo.save()
            return redirect("view_conversation", conversation_id=convo.id)

    return render(request, "messaging/rename_group.html", {
        "conversation": convo
    })

@login_required
def add_to_group(request, conversation_id):
    convo = get_object_or_404(Conversation, id=conversation_id)

    if request.method == "POST":
        username = request.POST.get("username", "").strip()

        # Check 1 — username exists
        user = User.objects.filter(username=username).first()
        if not user:
            return view_conversation(
                request,
                conversation_id,
                add_member_error="No user with that username exists."
            )

        # Check 2 — user already in group
        if user in convo.participants.all():
            return view_conversation(
                request,
                conversation_id,
                add_member_error="That user is already in this group."
            )

        # Valid → Add user
        convo.participants.add(user)
        return redirect("view_conversation", conversation_id=conversation_id)

    # GET redirect fallback
    return redirect("view_conversation", conversation_id=conversation_id)


@login_required
def update_nickname(request, conversation_id):
    conversation = get_object_or_404(Conversation, id=conversation_id)

    target_user_id = int(request.POST.get("target_user_id"))
    nickname = request.POST.get("nickname", "").strip()

    # Only allow editing nicknames of members
    if not conversation.participants.filter(id=target_user_id).exists():
        return redirect("view_conversation", conversation_id)

    ConversationNickname.objects.update_or_create(
        conversation=conversation,
        user_id=target_user_id,
        defaults={"nickname": nickname}
    )

    return redirect("view_conversation", conversation_id)