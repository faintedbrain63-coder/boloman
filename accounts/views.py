from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from accounts.forms import ProfileForm
from accounts.models import CustomerProfile


@login_required
def profile(request):
    customer, _created = CustomerProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = ProfileForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            request.user.first_name = data["first_name"]
            request.user.last_name = data["last_name"]
            request.user.save(update_fields=["first_name", "last_name"])
            customer.phone = data["phone"]
            customer.address_line = data["address_line"]
            customer.city = data["city"]
            customer.province = data["province"]
            customer.postal_code = data["postal_code"]
            customer.save()
            messages.success(request, "Profile saved.")
            return redirect("accounts:profile")
    else:
        form = ProfileForm(
            initial={
                "first_name": request.user.first_name,
                "last_name": request.user.last_name,
                "phone": customer.phone,
                "address_line": customer.address_line,
                "city": customer.city,
                "province": customer.province,
                "postal_code": customer.postal_code,
            }
        )
    return render(request, "accounts/profile.html", {"form": form, "profile": customer})
