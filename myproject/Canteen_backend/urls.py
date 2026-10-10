from django.urls import path
from .views import register,MyTokenObtainPairView,logout_and_blacklist, get_canteens, canteen_menu , move_order,update_cart_item
from .views import add_to_cart, view_cart, place_order, user_orders, remove_from_cart,current_user,orders_by_status, cancel_order, order_counts
from .views import admin_canteen_menu, admin_add_menu_item, admin_update_menu_item, admin_delete_menu_item, admin_toggle_menu_item
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('register/', register, name='register'),
    path('login/', MyTokenObtainPairView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', logout_and_blacklist, name='logout'),
    path('canteens/', get_canteens, name='get_canteens'),
    path('canteens/<uuid:canteen_id>/menu/', canteen_menu, name='canteen_menu'),
    path('cart/add/<uuid:canteen_id>/<int:product_id>', add_to_cart, name='add_to_cart'),
    path('cart/update/<uuid:canteen_id>/<int:product_id>', update_cart_item, name='update_cart_item'),
    path('cart/view/<uuid:canteen_id>', view_cart, name='view_cart'),
    path('cart/remove/<uuid:canteen_id>/<int:product_id>/',remove_from_cart),
    path("place_order/<uuid:canteen_id>/", place_order, name="place-order"),
    path('orders/', user_orders, name='user-orders'),
    path('orders/cancel/<int:order_id>/', cancel_order, name='cancel_order'),
    # for admin
    path("current-user/",current_user, name="current_user"),
    path("orders/counts/", order_counts, name="order_counts"),
    path("orders/<str:status>/", orders_by_status,name="moving-reg-to-orders"),
    path("orders/move/<str:status>/<int:order_id>/",move_order, name="move_order"),
    # for admin menu management
    path("admin/menu/<uuid:canteen_id>/", admin_canteen_menu, name="admin_canteen_menu"),
    path("admin/menu/add/", admin_add_menu_item, name="admin_add_menu_item"),
    path("admin/menu/update/<int:menu_id>/", admin_update_menu_item, name="admin_update_menu_item"),
    path("admin/menu/toggle/<int:menu_id>/", admin_toggle_menu_item, name="admin_toggle_menu_item"),
    path("admin/menu/delete/<int:menu_id>/", admin_delete_menu_item, name="admin_delete_menu_item"),
]


