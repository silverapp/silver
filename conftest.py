import pytest

from silver.fixtures.pytest_fixtures import *  # NOQA


pytest.register_assert_rewrite('silver.tests.api.specs.document_entry')
pytest.register_assert_rewrite('silver.tests.api.specs.utils')
