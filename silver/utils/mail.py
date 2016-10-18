from django.conf import settings
from django.core.mail import EmailMessage


def send_customer_email(customer, subject, body, from_email=None, cc=None, bcc=None):
    to = customer.emails
    cc = [cc] if cc else []
    bcc = [bcc] if bcc else []

    EmailMessage(subject=subject,
                 body=body,
                 from_email=(from_email or settings.FROM_EMAIL),
                 to=to,
                 bcc=bcc,
                 cc=cc).send()
