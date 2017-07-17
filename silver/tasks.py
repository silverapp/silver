from itertools import chain

from celery import group
from django.conf import settings
from redis.exceptions import LockError

from silver.models import Invoice, Proforma
from silver.vendors.celery_app import task
from silver.vendors.redis_server import redis


@task()
def generate_pdf(document_id, document_type):
    if document_type == 'Invoice':
        document = Invoice.objects.get(id=document_id)
    else:
        document = Proforma.objects.get(id=document_id)

    document.generate_pdf()


PDF_GENERATION_TIME_LIMIT = getattr(settings, 'PDF_GENERATION_TIME_LIMIT', 60)


@task(time_limit=PDF_GENERATION_TIME_LIMIT, ignore_result=True)
def generate_pdfs():
    lock = redis.lock('reconcile_new_domains_without_cert', timeout=PDF_GENERATION_TIME_LIMIT)

    if not lock.acquire(blocking=False):
        return

    dirty_documents = chain(Invoice.objects.filter(pdf__dirty=True),
                            Proforma.objects.filter(pdf__dirty=True))

    # Generate PDFs in parallel
    group(generate_pdf.s(document.id, document.kind)
          for document in dirty_documents)()

    try:
        lock.release()
    except LockError:
        pass
