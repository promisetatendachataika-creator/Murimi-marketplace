from django.urls import path

from . import api

app_name = "accounts"

urlpatterns = [
    path("me/", api.me, name="me"),                      # GET   who is logged in
    path("login/", api.login_view, name="login"),         # POST  {identifier, password}
    path("logout/", api.logout_view, name="logout"),      # POST
    path("register/", api.register, name="register"),     # POST  {name, phone, username?, email?, password, role}
    path("verify/", api.verify, name="verify"),           # POST  {code}
    path("resend/", api.resend, name="resend"),           # POST
    path("forgot/", api.forgot, name="forgot"),           # POST  {phone}
    path("password/", api.set_password, name="password"), # POST  {password}
]
