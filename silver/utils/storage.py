from django.core.files.storage import Storage


class MultipleStorage(Storage):
    def __init__(self, *storages):
        self.storages = storages

    def _open(self, name, mode='rb'):
        for storage in self.storages:
            try:
                return storage._open(name, mode)
            except IOError:
                pass

        raise IOError('File does not exist: %s' % name)

    def _save(self, name, content):
        for storage in self.storages:
            storage._save(name, content)

        return name
