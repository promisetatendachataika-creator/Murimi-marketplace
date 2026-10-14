from django.urls import path

from . import views

app_name = "web"

urlpatterns = [
    path("", views.index, name="index"),                                              # /
    path("login/", views.account_page, {"mode": "login"}, name="login"),              # /login/
    path("register/", views.account_page, {"mode": "register"}, name="register"),     # /register/
    path("forgot/", views.account_page, {"mode": "forgot"}, name="forgot"),           # /forgot/
    path("account/", views.my_account, name="account"),                              # /account/
    path("listing/<int:listing_id>/", views.listing_page, name="listing"),            # /listing/101/
]
