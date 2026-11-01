# Restful Booker API Tests

## Your Role

1. Act as an experienced QA engineer.
2. Use modern, proven practices when writing automated tests.

## Restful Booker Service

1. Service URL: https://restful-booker.herokuapp.com/
2. API documentation: https://restful-booker.herokuapp.com/apidoc/

## Test Requirements

1. Write tests in Python using pytest.
2. Choose the test structure yourself, following established practices.
3. Separate positive and negative tests for each endpoint into different files. Classify scenarios according to established testing theory.
4. Before each test session, check service availability using its Ping endpoint, if provided, or the host URL otherwise. Stop the remaining tests if the availability check fails after the configured retries. For Restful Booker, use a session-scoped autouse fixture: make up to three GET /ping attempts with a 5-second timeout and a 2-second delay between failed attempts. Continue on HTTP 201; retry connection errors, timeouts, and other statuses. After three failures, terminate pytest with exit code 2 and report the service URL and the reason for each failed attempt. Separate Ping tests are not required.
5. Validate response schemas for each endpoint.
6. Check value boundaries.
7. Organize test types logically into classes.
8. Run each test after writing it to verify its behavior.
9. When a test fails, first determine whether the cause is a service defect, an incorrect test, or an environment or test-data issue. Use xfail only for a confirmed service behavior that contradicts the documented contract. Set strict=True, describe the expected and actual behavior in the reason, and reference a defect report if one exists. Restrict xfail to the affected test or parameter case and the specific failure being documented; do not allow it to hide unrelated failures, including setup, cleanup, connection, or timeout errors. Report newly discovered discrepancies to the user before marking them as expected failures.
10. Do not perform load testing.
11. Use test-owned data for each test and delete it at the end of the test.
12. Do not use if statements in test bodies to handle different expected results for parameter cases. Move such cases into separate tests.
13. Treat GET requests to Restful Booker as operations that do not modify data; do not add separate checks that reading leaves records unchanged.
14. During cleanup, account for records already deleted by the test: DELETE 201 indicates successful cleanup; on DELETE 405, confirm absence with a subsequent GET expecting HTTP 404. Do not ignore other cleanup failures.

## Test Implementation Requirements

1. Use Poetry to manage project dependencies.
2. Use Git when developing tests.
3. Follow the principle of one commit per logically complete change.
4. Use Conventional Commits messages.
5. Create commits only after the user's approval.
6. Use linters and formatters of your choice, guided by the existing flake8, isort, and yapf configuration in setup.cfg.
7. Run formatting and lint checks before every commit.
8. Give every function a clear docstring. For all functions and methods except test functions, use Google-style docstrings: a short description and applicable Args, Returns or Yields, and Raises sections. Test docstrings should briefly describe the behavior being checked.
9. Write docstrings and code comments in English.
10. Add type annotations to functions.
11. Use assert statements with pytest assertion rewriting.
12. Arrange test bodies in this order: prepare parameters, execute the request, and verify the response.
13. Execute each service request on a separate line and store its result in a variable named response. Do not nest request execution inside a checker call's arguments.
14. Extract repeated checks into functions in checkers: general checks belong in common.py, while checks specific to tests in a particular directory belong in a separate module.
15. Checkers should accept response and expected values, and extract and validate response data internally. To verify persisted state, checkers may accept an API client, a record ID, and expected values; these checkers execute the request and validate its response themselves.
16. Register checker modules with pytest.register_assert_rewrite() before importing them.
17. Format pytest.mark.parametrize() values consistently and put case descriptions in the shared ids argument rather than individual pytest.param(..., id=...) calls.
18. When the documentation does not define the expected behavior, write a separate current-behavior test without xfail. Add an English comment in the test body explaining that the expected result is unspecified and the test records the service's current behavior.
19. When removing tests, also remove functions, fixtures, and imports that were used exclusively by those tests and are no longer needed.
20. Place data transformation helpers, excluding fixtures and checkers, in modules under the root helpers directory.
21. Place shared dataclasses such as Booking in helpers/models.py. Keep only ApiClient and its methods in tests/client.py.
22. Before creating a checker or any other function, check existing functions for duplicate functionality. Reuse a suitable function; when duplication is found, consolidate the implementations into a shared function and update the callers.
23. In tests, send requests through endpoint-specific ApiClient methods rather than a generic request() method. Each method name must match the corresponding endpoint's test directory name.
24. Store the host URL and endpoint paths in constants.py. Group constants logically and separate groups with short comments explaining their purpose.
25. Store authentication credentials in constants.py and read them from there; do not look up their values in environment variables.
26. Mark positive tests with pytest.mark.positive and negative tests with pytest.mark.negative. Do not use the integration marker instead.
27. After adding tests, provide a brief overview of the changes and verification results in the chat.
28. Write all future additions and updates to AGENTS.md in English only.

## Naming Requirements

1. Name directories under tests in snake_case based on the final functional name in the documentation URL: https://restful-booker.herokuapp.com/apidoc/#api-Booking-GetBookings → get_bookings.
2. Name test files in snake_case using test_{test_directory_name}_{positive/negative}.py: positive tests go in test_get_bookings_positive.py and negative tests in test_get_bookings_negative.py.
