from django.urls import path

from dashboard import views

app_name = "dashboard"

urlpatterns = [
    path("", views.overview, name="overview"),
    path("products/", views.product_list, name="products"),
    path("products/new/", views.product_edit, name="product_new"),
    path("products/<int:pk>/", views.product_edit, name="product_edit"),
    path("products/<int:pk>/delete/", views.product_delete, name="product_delete"),
    path("products/<int:product_pk>/variants/", views.variant_list, name="variants"),
    path("products/<int:product_pk>/variants/new/", views.variant_edit, name="variant_new"),
    path("products/<int:product_pk>/variants/generate/", views.variant_generate, name="variant_generate"),
    path("variants/<int:pk>/", views.variant_edit, name="variant_edit"),
    path("variants/<int:pk>/delete/", views.variant_delete, name="variant_delete"),
    path("categories/", views.category_list, name="categories"),
    path("categories/new/", views.category_edit, name="category_new"),
    path("categories/<int:pk>/", views.category_edit, name="category_edit"),
    path("categories/<int:pk>/delete/", views.category_delete, name="category_delete"),
    path("orders/", views.order_list, name="orders"),
    path("orders/<str:number>/cancel/", views.order_cancel, name="order_cancel"),
    path("orders/<str:number>/", views.order_detail, name="order_detail"),
    path("customers/", views.customer_list, name="customers"),
    path("messages/", views.message_list, name="messages"),
    path("messages/<int:pk>/toggle/", views.message_toggle, name="message_toggle"),
    path("settings/", views.site_settings_view, name="settings"),
    path("inventory/", views.inventory_list, name="inventory"),
    path("inventory/export/", views.inventory_export, name="inventory_export"),
    path("inventory/stock-in/", views.stock_in, name="stock_in"),
    path("inventory/adjust/", views.stock_adjust, name="stock_adjust"),
    path("inventory/movements/", views.movement_list, name="movements"),
]
