from itertools import chain

from silver.models import Invoice, Proforma
from silver.vendors.celery_app import task
from silver.vendors.redis_server import lock_manager


@task()
def generate_pdf(document_id, document_type):
    if document_type == 'Invoice':
        document = Invoice.objects.get(id=document_id)
    else:
        document = Proforma.objects.get(id=document_id)

    document.generate_pdf()


@task()
def generate_pdfs():
    lock = lock_manager.lock('generate_pdfs', 60000)
    if not lock:
        return

    tasks = []

    dirty_documents = chain(Invoice.objects.filter(pdf__dirty=True),
                            Proforma.objects.filter(pdf__dirty=True))

    async_results = list([
        tasks.append(generate_pdf.delay(document.id, document.kind))
        for document in dirty_documents
    ])

    for async_result in async_results:
        if async_result:
            async_result.get()

    lock_manager.unlock(lock)
