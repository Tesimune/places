from rest_framework import serializers
from .models import Place


class PlaceDto(serializers.ModelSerializer):
    class Meta:
        model = Place
        fields = ["id", "place_id", "name", "address", "latitude", "longitude", "created_at", "updated_at"]