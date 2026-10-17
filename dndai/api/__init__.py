# Порядок star-импортов значим (при совпадении имён побеждает последний):
# публичный http_session обязан приходить из openrouter — именно его объект
# используют тесты и api_request. Характеризующий тест:
# tests/test_package.py::test_package_http_session_comes_from_openrouter.
from .client import *
from .openrouter import *
from .prompts import *
