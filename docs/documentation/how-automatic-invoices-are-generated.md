---
title: How automated invoices are generated
description: Here you can find details regarding the process of generating automated invoices in Silver, for a better understanding of how the whole process works.
---

Each day a process runs and scans every active subscription. For each subscription schedules an invoicing job taking into account `generate_after`. The invoicing job has the following blueprint:
```
def invoicing(subscription, start_date, end_date):
```
