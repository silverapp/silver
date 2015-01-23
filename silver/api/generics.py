from silver.api.mixins import HPListModelMixin

from rest_framework.generics import GenericAPIView
from rest_framework.mixins import CreateModelMixin

from rest_framework_bulk.mixins import BulkCreateModelMixin


class HPListAPIView(GenericAPIView, HPListModelMixin):
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class HPListCreateAPIView(GenericAPIView, HPListModelMixin, CreateModelMixin):
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


class HPListBulkCreateAPIView(GenericAPIView, HPListModelMixin,
                              BulkCreateModelMixin):
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)