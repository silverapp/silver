from django.utils.deconstruct import deconstructible


@deconstructible
class PaymentProcessorBase(object):
    view_class = None
    payment_method_class = None

    def setup(self, data):
        """
            Sets up the Payment Processor
        """

        raise NotImplementedError

    def __repr__(self):
        return self.reference

    def __unicode__(self):
        return unicode(self.display_name)

    def __str__(self):
        return str(self.display_name)

    def __eq__(self, other):
        return self.__class__ is other.__class__

    def __ne__(self, other):
        return not self.__eq__(other)
