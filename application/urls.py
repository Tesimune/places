from django.urls import path
from . import views

urlpatterns = [
    path('', views.application, name='home'),
    path('api/search', views.search, name='search'),
    # path('api/nearby', views.nearby, name='nearby'),
    # path('api/geocode', views.geocode, name='geocode'),
    # path('api/details', views.details, name='details'),
]