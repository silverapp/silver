from rest_framework import generics, permissions

from silver.api.serializers.product_codes_serializer import ProductCodeSerializer
from silver.models import ProductCode


class ProductCodeListCreate(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ProductCodeSerializer
    queryset = ProductCode.objects.all()


class ProductCodeRetrieveUpdate(generics.RetrieveUpdateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ProductCodeSerializer
    queryset = ProductCode.objects.all()
