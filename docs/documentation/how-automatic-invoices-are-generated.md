Each day a process runs and scans every active subscription. For each subscription schedules an invoicing job taking into account `generate_after`. The invoicing job has the following blueprint:
```
def invoicing(subscription, start_date, end_date):
```
