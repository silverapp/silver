from optparse import make_option
from datetime import datetime as dt

from django.core.management.base import BaseCommand
from django.utils import translation
from django.conf import settings
from dateutil.relativedelta import *

from silver.documents_generator import DocumentsGenerator
from silver.models import Subscription


class Command(BaseCommand):
    help = 'Generates the billing documents (Invoices, Proformas).'
    option_list = BaseCommand.option_list + (
        make_option('--subscription',
            action='store',
            dest='subscription_id',
            type="int"),
        make_option('--date',
            action='store',
            dest='billing_date',
            type="string"),
    )

    def handle(self, *args, **options):
        translation.activate('en-us')

        date = None
        if options['billing_date']:
            billing_date = dt.strptime(options['billing_date'], '%Y-%m-%d').date()

        docs_generator = DocumentsGenerator()
        if options['subscription_id']:
            try:
                subscription = Subscription.objects.get(id=options['subscription_id'])
                docs_generator.generate(subscription=subscription)
                self.stdout.write('Done. You can have a Club-Mate now. :)')
            except Subscription.DoesNotExist:
                msg = 'The subscription with the provided id does not exist.'
                self.stdout.write(msg)
        else:
            docs_generator.generate(billing_date=billing_date)
            self.stdout.write('Done. You can have a Club-Mate now. :)')
