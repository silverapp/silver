from django.template.loader import select_template

from silver.utils.mail import send_customer_email


def send_transaction_email(transaction):
    data = {
        transaction.States.Initial: {
            'subject': u'New {} transaction',
            'file_path': 'new_payment_email.html',
        },
        transaction.States.Pending: {
            'subject': u'{} transaction being processed',
            'file_path': 'payment_processing_email.html',
        },
        transaction.States.Settled: {
            'subject': u'{} transaction settled',
            'file_path': 'payment_paid_email.html',
        },
        transaction.States.Failed: {
            'subject': u'{} transaction failed',
            'file_path': 'payment_failed_email.html',
        },
        transaction.States.Canceled: {
            'subject': u'{} transaction canceled',
            'file_path': 'payment_canceled_email.html',
        },
        transaction.States.Refunded: {
            'subject': u'{} transaction refunded',
            'file_path': 'payment_refunded_email.html',
        },
    }

    file_path = data[transaction.state]['file_path']
    subject = data[transaction.state]['subject'].format(
        transaction.provider.name
    )

    templates = [
        'payments/{}/{}'.format(transaction.provider.slug, file_path),
        'payments/{}'.format(file_path)
    ]
    template = select_template(templates)
    body = template.render({
        'transaction': transaction,
        'customer': transaction.customer,
    })

    from_email = transaction.provider.display_email

    send_customer_email(transaction.customer, subject=subject, body=body,
                        from_email=from_email)
