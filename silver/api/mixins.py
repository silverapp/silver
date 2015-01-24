from django.core.paginator import EmptyPage

from rest_framework.response import Response
from rest_framework.templatetags.rest_framework import replace_query_param


class HPListModelMixin(object):
    """
    List a queryset.
    """
    empty_error = "Empty list and '%(class_name)s.allow_empty' is False."
    page_field = 'page'

    def list(self, request, *args, **kwargs):
        self.object_list = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(self.object_list)
        headers = {}
        if page is not None:
            headers = self.get_pagination_headers(request, page)

        serializer = self.get_serializer(page, many=True)

        return Response(serializer.data, headers=headers)

    def get_pagination_headers(self, request, page):
        links = []
        url = request and request.build_absolute_uri() or ''

        siblings = {
            'first': lambda p: p.paginator.page_range[0],
            'prev': lambda p: p.previous_page_number(),
            'next': lambda p: p.next_page_number(),
            'last': lambda p: p.paginator.page_range[-1],
        }

        for rel, get_page_number in siblings.items():
            try:
                page_url = replace_query_param(url, self.page_field,
                                               get_page_number(page))
                links.append('<%s>; rel="%s"' % (page_url, rel))
            except EmptyPage:
                pass

        headers = {
            'X-Result-Count': page.paginator.count,
        }

        if links:
            headers['Link'] = ', '.join(links)

        return headers
