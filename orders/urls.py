from django.urls import path

from orders import views

app_name = "orders"

urlpatterns = [
    path("checkout/", views.checkout, name="checkout"),
    path("confirmation/<str:number>/", views.confirmation, name="confirmation"),
    path("mine/", views.order_list, name="list"),
    path("mine/<str:number>/", views.order_detail, name="detail"),
    path("mine/<str:number>/cancel/", views.cancel_order, name="cancel"),
]
