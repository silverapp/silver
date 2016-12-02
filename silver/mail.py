from django.template.loader import select_template
from silver.utils.mail import send_customer_email


def send_new_transaction_email(transaction):
    subject = u'New {} transaction'.format(transaction.provider.name)

    templates = [
        'payments/{}/new_payment_email.html'.format(transaction.provider.slug),
        'payments/new_payment_email.html'
    ]

    template = select_template(templates)
    body = template.render({
        'transaction': transaction,
        'customer': transaction.customer,
    })

    from_email = transaction.provider.display_email

    send_customer_email(transaction.customer, subject=subject, body=body,
                        from_email=from_email)


def send_pending_transaction_email(transaction):
    subject = u'{} transaction being processed'.format(transaction.provider.name)

    templates = [
        'payments/{}/payment_processing_email.html'.format(
            transaction.provider.slug
        ),
        'payments/payment_processing_email.html'
    ]

    template = select_template(templates)
    body = template.render({
        'transaction': transaction,
        'customer': transaction.customer,
    })

    from_email = transaction.provider.display_email

    send_customer_email(transaction.customer, subject=subject, body=body,
                        from_email=from_email)


def send_settled_transaction_email(transaction):
    subject = u'{} transaction settled'.format(transaction.provider.name)

    templates = [
        'payments/{}/payment_paid_email.html'.format(transaction.provider.slug),
        'payments/payment_paid_email.html'
    ]

    template = select_template(templates)
    body = template.render({
        'transaction': transaction,
        'customer': transaction.customer,
    })

    from_email = transaction.provider.display_email

    send_customer_email(transaction.customer, subject=subject, body=body,
                        from_email=from_email)


def send_failed_transaction_email(transaction):
    subject = u'{} transaction failed'.format(transaction.provider.name)

    templates = [
        'payments/{}/payment_failed_email.html'.format(transaction.provider.slug),
        'payments/payment_failed_email.html'
    ]

    template = select_template(templates)
    body = template.render({
        'transaction': transaction,
        'customer': transaction.customer,
    })

    from_email = transaction.provider.display_email

    send_customer_email(transaction.customer, subject=subject, body=body,
                        from_email=from_email)


def send_canceled_transaction_email(transaction):
    subject = u'{} transaction canceled'.format(transaction.provider.name)

    templates = [
        'payments/{}/payment_canceled_email.html'.format(transaction.provider.slug),
        'payments/payment_canceled_email.html'
    ]

    template = select_template(templates)
    body = template.render({
        'transaction': transaction,
        'customer': transaction.customer,
    })

    from_email = transaction.provider.display_email

    send_customer_email(transaction.customer, subject=subject, body=body,
                        from_email=from_email)


def send_refunded_transaction_email(transaction):
    subject = u'{} transaction refunded'.format(transaction.provider.name)

    templates = [
        'payments/{}/payment_refunded_email.html'.format(transaction.provider.slug),
        'payments/payment_refunded_email.html'
    ]

    template = select_template(templates)
    body = template.render({
        'transaction': transaction,
        'customer': transaction.customer,
    })

    from_email = transaction.provider.display_email

    send_customer_email(transaction.customer, subject=subject, body=body,
                        from_email=from_email)
