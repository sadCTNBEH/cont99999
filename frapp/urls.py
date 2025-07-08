from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.index, name='index'),
    path('analyze', views.analyze, name='analyze'),
    path('add_image', views.add_image, name='add_image'),
    path('delete_image/', views.delete_image, name='delete_image'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='frapp/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('info/', views.info, name='info'),
    path('backdoor/', views.backdoor, name='backdoor'),
]
