import datetime as dt
from datetime import datetime
from optparse import make_option

from django.core.management.base import BaseCommand
from django.utils import timezone

from silver.models import Subscription, BillingLog


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--date',
            action='store',
            dest='date'),
    )

    def handle(self, *args, **options):
        if options['date']:
            date = datetime.strptime(options['date'], '%Y-%m-%d')
        else:
            now = timezone.now().date()
            date = dt.date(now.year, now.month - 1, 1)

        for subscription in Subscription.objects.all():
            self.stdout.write('Tweaking for subscription %d' % subscription.id)
            BillingLog.objects.create(subscription=subscription,
                                      billing_date=date)
