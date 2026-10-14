"""
/api/auth/... : log in, log out, register, WhatsApp codes, forgot password.

Session log-in: after a successful log-in Django sets a "sessionid" cookie, and every
later request from that browser is that user (request.user). Every POST needs the
CSRF token in the X-CSRFToken header (api.js sends it).

Rules kept from the Hub:
- 5 log-in tries per 15 minutes, then "wait".
- The same message for a wrong number and a wrong password (nobody can test who has an account).
- "Forgot password" answers the same whether or not the number has an account.
- Codes stored only as HMAC fingerprints.
"""
import re

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone

from core.http import (allow, clear_failures, client_ip, json_error, rate_limited, read_json,
                       record_failure, too_many_failures)

from .choices import ROLE_CHOICES
from .models import PhoneCode, User
from .phone import try_normalize_phone
from .whatsapp import send_code

LOGIN_LIMIT, LOGIN_WINDOW = 5, 15 * 60          # 5 tries per 15 minutes
RESEND_GAP = 60                                 # seconds between codes to one number
CODES_PER_HOUR = 5
USERNAME_RE = re.compile(r"^[a-z0-9_]{3,30}$")

# Where the session remembers who is waiting for a code
SESSION_PHONE, SESSION_PURPOSE, SESSION_RESET_OK = "code_phone", "code_purpose", "reset_ok_phone"


def _send_new_code(request, phone, purpose):
    """Issue + send a code, with limits so nobody can flood a number with messages."""
    if rate_limited(f"code-gap:{phone}", 1, RESEND_GAP):
        return json_error("Please wait a minute before asking for another code.", status=429)
    if rate_limited(f"code-hour:{phone}", CODES_PER_HOUR, 3600):
        return json_error("Too many codes for this number. Please try again in an hour.", status=429)
    code = PhoneCode.issue(phone, purpose)
    send_code(phone, code, purpose)
    request.session[SESSION_PHONE] = phone
    request.session[SESSION_PURPOSE] = purpose
    return None


@allow("GET")
def me(request):
    """Who is logged in? {"user": {...}} or {"user": null}."""
    return JsonResponse({"user": request.user.as_json() if request.user.is_authenticated else None})


@allow("POST")
def login_view(request):
    data, err = read_json(request)
    if err:
        return err
    identifier = str(data.get("identifier", "")).strip()
    password = str(data.get("password", ""))
    errors = {}
    if not identifier:
        errors["identifier"] = "Enter your WhatsApp number, username or email."
    if not password:
        errors["password"] = "Enter your password."
    if errors:
        return json_error("Please check the form.", errors=errors)

    # Only WRONG tries count: 5 per account, 20 per network address, within 15 minutes.
    # (A farmer logging in on two phones in one morning must not be locked out.)
    per_account = f"login-fail:{identifier.lower()}"
    per_address = f"login-fail-ip:{client_ip(request)}"
    if too_many_failures(per_account, LOGIN_LIMIT) or too_many_failures(per_address, LOGIN_LIMIT * 4):
        return json_error("Too many tries. Please wait 15 minutes and try again.", status=429)

    user = authenticate(request, username=identifier, password=password)
    if user is None:
        record_failure(per_account, LOGIN_WINDOW)
        record_failure(per_address, LOGIN_WINDOW)
        return json_error("That number, username, email or password isn't right.")
    clear_failures(per_account)                  # a correct log-in wipes this account's count
    login(request, user)                         # sets the session cookie
    return JsonResponse({"user": user.as_json()})


@allow("POST")
def logout_view(request):
    logout(request)
    return JsonResponse({"user": None})


@allow("POST")
def register(request):
    data, err = read_json(request)
    if err:
        return err
    name = str(data.get("name", "")).strip()
    phone = try_normalize_phone(data.get("phone"))
    username = str(data.get("username", "") or "").strip().lower()
    email = str(data.get("email", "") or "").strip().lower()
    password = str(data.get("password", ""))
    role = str(data.get("role", ""))

    errors = {}
    if not name:
        errors["name"] = "Tell us your name."
    elif len(name) > 60:
        errors["name"] = "Use 60 characters or fewer."
    if not phone:
        errors["phone"] = "Enter a Zimbabwe mobile number, like 077 123 4567."
    if role not in dict(ROLE_CHOICES):
        errors["role"] = "Choose what you want to do."
    if username and not USERNAME_RE.match(username):
        errors["username"] = "3 to 30 letters, numbers or _ only."
    if email:
        try:
            validate_email(email)
        except ValidationError:
            errors["email"] = "That doesn't look like an email address."

    # An unconfirmed sign-up (is_active False) may be replaced; a confirmed account may not.
    existing = User.objects.filter(phone=phone).first() if phone else None
    if existing and existing.is_active:
        errors["phone"] = "This number already has an account. Try logging in."
    # Only an UNFINISHED sign-up for this same number may keep its own username/email.
    replaceable = existing.pk if existing and not existing.is_active else None
    if username and User.objects.filter(username=username).exclude(pk=replaceable).exists():
        errors["username"] = "That username is taken."
    if email and User.objects.filter(email=email).exclude(pk=replaceable).exists():
        errors["email"] = "That email is already used by another account."

    if "password" not in errors:
        try:
            validate_password(password, User(name=name, phone=phone or "", username=username or None, email=email or None))
        except ValidationError as e:
            errors["password"] = " ".join(e.messages)
    if errors:
        return json_error("Please check the form.", errors=errors)

    with transaction.atomic():
        user = existing or User(phone=phone)
        user.name, user.username, user.email, user.role = name, username or None, email or None, role
        user.is_active = False                   # switched on when the WhatsApp code is confirmed
        user.set_password(password)
        user.save()
    problem = _send_new_code(request, phone, PhoneCode.PURPOSE_REGISTER)
    if problem:
        return problem
    return JsonResponse({"phone": phone, "code_sent": True}, status=201)


@allow("POST")
def verify(request):
    """Check the 6-digit code for the number waiting in this session."""
    data, err = read_json(request)
    if err:
        return err
    phone = request.session.get(SESSION_PHONE)
    purpose = request.session.get(SESSION_PURPOSE)
    if not phone or not purpose:
        return json_error("Your code has expired. Please start again.")
    code = str(data.get("code", "")).strip()
    if not re.fullmatch(r"\d{6}", code):
        return json_error("Please check the code.", errors={"code": "Enter the 6 digits from WhatsApp."})
    if not PhoneCode.verify_code(phone, purpose, code):
        return json_error("Please check the code.",
                          errors={"code": "That code isn't right, or it has expired. Check the latest WhatsApp message."})

    for key in (SESSION_PHONE, SESSION_PURPOSE):
        request.session.pop(key, None)
    if purpose == PhoneCode.PURPOSE_REGISTER:
        user = User.objects.get(phone=phone)
        user.is_active = True
        user.phone_verified_at = timezone.now()
        user.save(update_fields=["is_active", "phone_verified_at"])
        login(request, user, backend="accounts.backends.PhoneUsernameEmailBackend")
        return JsonResponse({"user": user.as_json(), "next": "done"})
    request.session[SESSION_RESET_OK] = phone   # reset: allowed to choose a new password now
    return JsonResponse({"next": "new_password"})


@allow("POST")
def resend(request):
    phone = request.session.get(SESSION_PHONE)
    purpose = request.session.get(SESSION_PURPOSE)
    if not phone or not purpose:
        return json_error("Please start again.")
    if purpose == PhoneCode.PURPOSE_RESET and not User.objects.filter(phone=phone, is_active=True).exists():
        return JsonResponse({"code_sent": True})      # same answer as a real number
    problem = _send_new_code(request, phone, purpose)
    return problem or JsonResponse({"code_sent": True})


@allow("POST")
def forgot(request):
    """Start a password reset. Always the same answer, so nobody learns which numbers have accounts."""
    data, err = read_json(request)
    if err:
        return err
    phone = try_normalize_phone(data.get("phone"))
    if not phone:
        return json_error("Please check the form.", errors={"phone": "Enter a Zimbabwe mobile number, like 077 123 4567."})
    if User.objects.filter(phone=phone, is_active=True).exists():
        problem = _send_new_code(request, phone, PhoneCode.PURPOSE_RESET)
        if problem and problem.status_code == 429:
            return problem
    else:
        request.session[SESSION_PHONE] = phone           # behave the same; no code is sent
        request.session[SESSION_PURPOSE] = PhoneCode.PURPOSE_RESET
    return JsonResponse({"phone": phone, "code_sent": True})


@allow("POST")
def set_password(request):
    """Choose a new password, only after a correct reset code in this session."""
    data, err = read_json(request)
    if err:
        return err
    phone = request.session.get(SESSION_RESET_OK)
    user = User.objects.filter(phone=phone, is_active=True).first() if phone else None
    if not user:
        return json_error("Please start the password reset again.")
    password = str(data.get("password", ""))
    try:
        validate_password(password, user)
    except ValidationError as e:
        return json_error("Please check the form.", errors={"password": " ".join(e.messages)})
    user.set_password(password)
    user.save(update_fields=["password"])
    request.session.pop(SESSION_RESET_OK, None)
    return JsonResponse({"done": True})
