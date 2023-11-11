# Unit Tests

### Prerequisites

Install the dependencies in `requirements-dev.txt`. These are not part of the normal dependencies to prevent installing
them for end users.

```
pip install -r requirements-dev.txt
```

### Running unit tests

Pytest will detect pretty much all `test*` folders and python files and run functions that start with `test`.

```
pytest

===================================================== test session starts =====================================================
...
collected 5 items                                                                                                             

test/test_config.py .....                                                                                               [100%]

====================================================== 5 passed in 0.33s ======================================================
```

A specific file can also be run, instead of collecting and running all tests:

```
pytest test_config.py

===================================================== test session starts =====================================================
...
collected 5 items                                                                                                             

test/test_config.py .....                                                                                               [100%]

====================================================== 5 passed in 0.33s ======================================================
```

The `-v` flag provides additional information, and we can use `-k` to run tests matching a specific expression.

```
pytest -k defaults -vvv
===================================================== test session starts =====================================================
...
collected 5 items / 4 deselected / 1 selected                                                                                 

test/test_config.py::test_config[defaults load correctly] PASSED                                                        [100%]

=============================================== 1 passed, 4 deselected in 0.30s ===============================================
```
