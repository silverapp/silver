from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError

from silver.models.subscription import Subscription
from silver.utils import get_object_or_None


class MeteredFeatureUnitsLog(models.Model):
    metered_feature = models.ForeignKey('MeteredFeature', related_name='consumed')
    subscription = models.ForeignKey('Subscription', related_name='mf_log_entries')
    consumed_units = models.DecimalField(max_digits=19, decimal_places=4,
                                         validators=[MinValueValidator(0.0)])
    start_date = models.DateField(editable=False)
    end_date = models.DateField(editable=False)

    class Meta:
        unique_together = ('metered_feature', 'subscription', 'start_date',
                           'end_date')

    def clean(self):
        super(MeteredFeatureUnitsLog, self).clean()
        if self.subscription.state in [Subscription.STATES.ENDED,
                                       Subscription.STATES.INACTIVE]:
            if not self.id:
                action_type = "create"
            else:
                action_type = "change"
            err_msg = 'You cannot %s a metered feature units log belonging to '\
                      'an %s subscription.' % (action_type,
                                               self.subscription.state)
            raise ValidationError(err_msg)

        if not self.id:
            start_date = self.subscription.bucket_start_date()
            end_date = self.subscription.bucket_end_date()
            if get_object_or_None(MeteredFeatureUnitsLog, start_date=start_date,
                                  end_date=end_date,
                                  metered_feature=self.metered_feature,
                                  subscription=self.subscription):
                err_msg = 'A %s units log for the current date already exists.'\
                          ' You can edit that one.' % self.metered_feature
                raise ValidationError(err_msg)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.id:
            if not self.start_date:
                self.start_date = self.subscription.bucket_start_date()
            if not self.end_date:
                self.end_date = self.subscription.bucket_end_date()
            super(MeteredFeatureUnitsLog, self).save(force_insert, force_update,
                                                     using, update_fields)

        if self.id:
            update_fields = []
            for field in self._meta.fields:
                if field.name != 'metered_feature' and field.name != 'id':
                    update_fields.append(field.name)
            super(MeteredFeatureUnitsLog, self).save(
                update_fields=update_fields)

    def __unicode__(self):
        return self.metered_feature.name
