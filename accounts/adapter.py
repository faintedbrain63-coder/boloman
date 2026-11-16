from django.urls import reverse

from allauth.account.adapter import DefaultAccountAdapter


class AccountAdapter(DefaultAccountAdapter):
    def get_login_redirect_url(self, request):
        url = super().get_login_redirect_url(request)
        home = reverse("home")
        if request.user.is_staff and url in {home, "/"}:
            return reverse("dashboard:overview")
        return url
