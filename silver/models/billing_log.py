from django.db import models


class BillingLog(models.Model):
    subscription = models.ForeignKey('Subscription',
                                     related_name='billing_log_entries')
    invoice = models.ForeignKey('Invoice', null=True, blank=True,
                                related_name='billing_log_entries')
    proforma = models.ForeignKey('Proforma', null=True, blank=True,
                                 related_name='billing_log_entries')
    billing_date = models.DateField(
        help_text="The date when the invoice/proforma was issued."
    )

    class Meta:
        ordering = ['-billing_date']

    def __unicode__(self):
        return '{sub} - {pro} - {inv} - {date}'.format(
            sub=self.subscription, pro=self.proforma,
            inv=self.invoice, date=self.billing_date)
