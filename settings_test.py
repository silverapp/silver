from settings import *

triggered_processor = 'triggered'
manual_processor = 'manual'
failing_void_processor = 'failing_void'

PAYMENT_PROCESSORS = {
    triggered_processor: {
        'class': 'silver.tests.fixtures.TriggeredProcessor'
    },
    manual_processor: {
        'class': 'silver.tests.fixtures.ManualProcessor'
    },
    failing_void_processor: {
        'class': 'silver.tests.fixtures.FailingVoidTriggeredProcessor'
    }

}
