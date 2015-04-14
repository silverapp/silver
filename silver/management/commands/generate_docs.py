from optparse import make_option

from django.core.management.base import BaseCommand
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
    )

    def handle(self, *args, **options):
        docs_generator = DocumentsGenerator()
        if options['subscription_id']:
            try:
                subscription = Subscription.objects.get(id=options['subscription_id'])
                docs_generator.generate(subscription)
                self.stdout.write('Done. You can have a Club-Mate now. :)')
            except Subscription.DoesNotExist:
                msg = 'The subscription with the provided id does not exist.'
                self.stdout.write(msg)
        else:
            docs_generator.generate()
            self.stdout.write('Done. You can have a Club-Mate now. :)')
