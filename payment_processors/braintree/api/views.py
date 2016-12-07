from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view('GET')
def client_token(request, payment_method=None, payment_processor=None):
    if payment_method:
        payment_processor = payment_method.payment_processor
    elif not payment_processor:
        return Response(
            {'detail': 'A payment method or a payment processor is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    token = payment_method.client_token or payment_processor.client_token

    if not token:
        return Response({'detail': 'Braintree miscommunication.'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response({'token': token}, status=status.HTTP_200_OK)
