from django import forms
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordResetForm
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .models import AccountProfile, User


class UserCreateForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    is_active = forms.BooleanField(required=False, initial=True, label="Active")

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "username",
            "email",
            "phone",
            "role",
            "password",
            "is_active",
        ]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.is_active = self.cleaned_data.get("is_active", True)
        if commit:
            user.save()
            AccountProfile.objects.get_or_create(
                user=user,
                defaults={
                    "role": user.role,
                    "phone": user.phone,
                    "department": user.department,
                },
            )
        return user


class UserUpdateForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, required=False, help_text="Leave blank to keep the current password.")
    is_active = forms.BooleanField(required=False, label="Active")

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "username",
            "email",
            "phone",
            "role",
            "password",
            "is_active",
        ]

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        user.is_active = self.cleaned_data.get("is_active", user.is_active)
        if commit:
            user.save()
            profile, _ = AccountProfile.objects.get_or_create(user=user)
            profile.role = user.role
            profile.phone = user.phone
            profile.department = user.department
            profile.save()
        return user


@login_required
def account_index(request):
    if request.user.is_super_admin():
        profiles = AccountProfile.objects.select_related("user").all()[:10]
        users = User.objects.all().order_by("username")
        return render(request, "accounts/index.html", {"profiles": profiles, "users": users})

    return render(request, "accounts/index.html", {"user": request.user})


@login_required
def user_management(request):
    if not request.user.is_super_admin():
        messages.error(request, "You do not have permission to manage users.")
        return redirect("accounts:role_redirect")

    form = UserCreateForm()
    if request.method == "POST":
        form = UserCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "User created successfully.")
            return redirect("accounts:user_management")

    query = request.GET.get("q", "").strip()
    users = User.objects.all()
    if query:
        users = users.filter(
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
            | Q(phone__icontains=query)
            | Q(role__icontains=query)
        )
    users = users.order_by("username")
    page = request.GET.get("page", 1)
    paginator = Paginator(users, 15)
    users = paginator.get_page(page)

    query_params = request.GET.copy()
    if "page" in query_params:
        del query_params["page"]

    return render(request, "accounts/user_management.html", {
        "form": form,
        "users": users,
        "query": query,
        "page_obj": users,
        "querystring": query_params.urlencode(),
    })


@login_required
def user_edit(request, pk):
    if not request.user.is_super_admin():
        messages.error(request, "You do not have permission to manage users.")
        return redirect("accounts:role_redirect")

    user = get_object_or_404(User, pk=pk)
    form = UserUpdateForm(request.POST or None, instance=user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "User updated successfully.")
        return redirect("accounts:user_management")

    return render(request, "accounts/user_edit.html", {"form": form, "edit_user": user})


@login_required
def user_toggle_active(request, pk):
    if not request.user.is_super_admin():
        messages.error(request, "You do not have permission to manage users.")
        return redirect("accounts:role_redirect")

    user = get_object_or_404(User, pk=pk)
    user.is_active = not user.is_active
    user.save()
    status = "activated" if user.is_active else "deactivated"
    messages.success(request, f"User {user.username} has been {status}.")
    return redirect("accounts:user_management")


@login_required
def user_delete(request, pk):
    if not request.user.is_super_admin():
        messages.error(request, "You do not have permission to manage users.")
        return redirect("accounts:role_redirect")

    user = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        username = user.username
        user.delete()
        messages.success(request, f"User {username} deleted successfully.")
        return redirect("accounts:user_management")

    return render(request, "accounts/user_delete.html", {"delete_user": user})


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "")
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            user.ensure_profiles()
            login(request, user)
            return redirect("accounts:role_redirect")
        messages.error(request, "Invalid username or password.")
    return render(request, "accounts/login.html")


@login_required
def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def role_redirect(request):
    if request.user.is_lab_staff():
        return redirect("tracking:lab_dashboard")
    return redirect("tracking:dashboard")


def password_reset_view(request):
    if request.method == "POST":
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            form.save(
                request=request,
                use_https=request.is_secure(),
                email_template_name="registration/password_reset_email.html",
                subject_template_name="registration/password_reset_subject.txt",
            )
            messages.success(request, "If an account exists for that email, reset instructions have been sent.")
            return redirect("login")
    else:
        form = PasswordResetForm()
    return render(request, "accounts/password_reset.html", {"form": form})
