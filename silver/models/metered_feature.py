from django.db import models
from django.core.validators import MinValueValidator


class UnsavedForeignKey(models.ForeignKey):
    allow_unsaved_instance_assignment = True


class MeteredFeature(models.Model):
    name = models.CharField(
        max_length=200,
        help_text='The feature display name.',
        db_index=True,
    )
    unit = models.CharField(max_length=20)
    price_per_unit = models.DecimalField(
        max_digits=19, decimal_places=4, validators=[MinValueValidator(0.0)],
        help_text='The price per unit.',
    )
    included_units = models.DecimalField(
        max_digits=19, decimal_places=4, validators=[MinValueValidator(0.0)],
        help_text='The number of included units per plan interval.'
    )
    included_units_during_trial = models.DecimalField(
        max_digits=19, decimal_places=4, validators=[MinValueValidator(0.0)],
        blank=True, null=True,
        help_text='The number of included units during the trial period.'
    )
    product_code = UnsavedForeignKey(
        'ProductCode', help_text='The product code for this plan.'
    )

    class Meta:
        ordering = ('name',)

    def __unicode__(self):
        fmt = u'{name} ({price:.2f}$, {included:.2f} included)'
        return fmt.format(name=self.name, price=self.price_per_unit,
                          included=self.included_units)
