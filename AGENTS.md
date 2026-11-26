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
9. When a test fails, first determine whether the cause is a service defect, an incorrect test, or an environment or test-data issue. Use xfail only for a confirmed service behavior that contradicts the documented contract. Set strict=True, describe the expected and actual behavior in the reason, and reference a defect report if one exists. Restrict xfail to the affected test or parameter case and use raises with a dedicated response-value mismatch exception rather than AssertionError. Validate HTTP status, media type, parsing, required fields, and JSON types independently before comparing values. Calendar-value mismatches, including confirmed malformed dates, may be treated as value differences after structural validation. For a confirmed malformed response representation, use a separate exception for that known serialization failure and validate the HTTP status independently. Whole-response value comparisons are allowed: do not introduce field-specific defect recognition solely to narrow xfail. Accept that other value differences within the marked scenario may also be classified as expected; cover those values in unmarked scenarios. Never classify setup, cleanup, connection, or timeout errors as expected. Cleanup must report failures with CleanupError, which must not inherit from AssertionError or a response-mismatch exception, after attempting deletion of every known ID. Report newly discovered discrepancies to the user before marking them as expected failures.
10. Do not perform load testing.
11. Use test-owned data for each test and attempt to delete it at the end of the test. Assume an isolated test environment where only the tester creates records. Delete records by their registered IDs without pre-deletion ownership or UUID checks; retain the cleanup status handling in item 14. There is no direct database access, so API-based cleanup cannot guarantee removal of every test record, including records created before a setup failure whose IDs cannot be recovered. The current ID registration, recovery, and deletion mechanisms are accepted with this limitation; exhaustive cleanup guarantees are not a completion requirement. Continue attempting deletion of registered records and report detected cleanup failures explicitly; this limitation does not permit suppressing those failures.
12. Do not use if statements in test bodies to handle different expected results for parameter cases. Move such cases into separate tests.
13. Treat GET requests to Restful Booker as operations that do not modify data; do not add separate checks that reading leaves records unchanged.
14. Use the shared cleanup_bookings function in checkers/common.py for test-data cleanup. DELETE 201 indicates successful cleanup; on DELETE 405, confirm absence with a subsequent GET expecting HTTP 404, without imposing a response body or media type on that confirmation. Attempt cleanup of the remaining registered IDs after a failure and report all detected failures with CleanupError.

## Git Workflow

1. Before making changes for a new task, switch to the local main branch and update it from the remote repository with git pull --ff-only origin main.
2. Create a new task-specific branch from the updated main before editing files. Do not implement a new task directly on main or reuse a previous task's branch. Creating commits still requires the user's separate approval.
3. Treat code and documentation work discussed in a side chat as part of the parent task. Use the same task branch for all edits, reviews, and checks in that side chat.
4. Store temporary files created for project work in `.project-tmp/` at the repository root. Exclude this directory locally via `.git/info/exclude`.

## Test Implementation Requirements

1. Use Poetry to manage project dependencies.
2. Use Git when developing tests.
3. Follow the principle of one commit per logically complete change.
4. Use Conventional Commits messages.
5. Create commits only after the user's approval.
6. Use flake8 for linting, isort for import sorting, and yapf for code formatting, following their configuration in setup.cfg.
7. Run formatting and lint checks before every commit.
8. Give every function a clear docstring. For all functions and methods except test functions, use Google-style docstrings: a short description and applicable Args, Returns or Yields, and Raises sections. Test docstrings should briefly describe the behavior being checked.
9. Write docstrings and code comments in English.
10. Add type annotations to functions.
11. Use assert statements with pytest assertion rewriting.
12. Arrange test bodies in this order: prepare parameters, execute the request, and verify the response.
13. Execute each service request on a separate line and store its result in a variable named response. Do not nest request execution inside a checker call's arguments.
14. Extract repeated checks into functions in checkers. Place checks shared across endpoint test groups in common.py, including shared booking response, schema, and persistence checks. Place endpoint-specific checks in a module named after the corresponding test directory, such as get_bookings.py or create_token.py.
15. Checkers should accept response and expected values, and extract and validate response data internally. Validate the response schema before comparing field values. Keep type and structure checks in the schema stage only. For current-behavior responses with a different shape, use a custom schema based on the expected fields and types. To verify persisted state, checkers may accept an API client, a record ID, and expected values; these checkers execute the request and validate its response themselves.
16. Register checker modules with pytest.register_assert_rewrite() before importing them.
17. Format pytest.mark.parametrize() values consistently and put case descriptions in the shared ids argument rather than individual pytest.param(..., id=...) calls.
18. When the documentation does not define the expected behavior, write a separate current-behavior test without xfail and mark it with pytest.mark.current_behavior in addition to positive or negative. This marker classifies observed behavior and does not change the test outcome. Add an English comment in the test body explaining that the expected result is unspecified and the test records the service's current behavior.
19. When removing tests, also remove functions, fixtures, and imports that were used exclusively by those tests and are no longer needed.
20. Place data transformation helpers, excluding fixtures and checkers, in modules under the root helpers directory.
21. Place shared dataclasses such as Booking in helpers/models.py. Keep only ApiClient and its methods in tests/client.py.
22. Before creating a checker or any other function, check existing functions for duplicate functionality. Reuse a suitable function; when duplication is found, consolidate functions with the same responsibility and semantics into a shared function and update the callers. Avoid universal functions with numerous behavioral switches; superficial code similarity alone is not a reason to merge functions.
23. In tests, send requests through endpoint-specific ApiClient methods rather than a generic request() method. Each method name must match the corresponding endpoint's test directory name. Each method must validate the HTTP status before returning the response. Default expected_status_code to the documented success status for that endpoint and pass other expected statuses explicitly at the call site.
24. Store the host URL and endpoint paths in constants.py. Group constants logically and separate groups with short comments explaining their purpose.
25. Store authentication credentials in constants.py and read them from there; do not look up their values in environment variables.
26. Mark positive tests with pytest.mark.positive and negative tests with pytest.mark.negative. Do not use the integration marker instead.
27. After adding tests, provide a brief overview of the changes and verification results in the chat.
28. Write all future additions and updates to AGENTS.md in English only.

## Naming Requirements

1. Name directories under tests in snake_case based on the final functional name in the documentation URL: https://restful-booker.herokuapp.com/apidoc/#api-Booking-GetBookings → get_bookings.
2. Name test files in snake_case using test_{test_directory_name}_{positive/negative}.py: positive tests go in test_get_bookings_positive.py and negative tests in test_get_bookings_negative.py.

## Project Element Naming

1. Name endpoint-specific response checkers `check_<endpoint>_response`, using the full endpoint name from the API documentation in snake_case. For example, use `check_delete_booking_response` for `DeleteBooking`.
2. When tests cover multiple response formats for an endpoint, place the format immediately before `response`: `check_<endpoint>_<format>_response` (for example, `check_create_booking_xml_response`). Use `json`, `xml`, or `form` for the corresponding response representation. Shared checkers use the same format suffix, for example `check_booking_json_response`.

## Completion Criteria

1. Implement the requested behavior within the agreed scope.
2. Run new and modified tests. When shared components change, run the affected existing scenarios as regression checks. Run the full suite when the scope and risk of the change justify it; do not require a full run after every edit.
3. Leave no unexplained test failures or setup and cleanup errors. Any xfail must satisfy the requirements for confirmed documented-contract discrepancies in Test Requirements.
4. Ensure formatting and lint checks pass. For documentation-only changes, validate the edited content and relevant references; run code checks when applicable and always before a commit as required above.
5. Update documentation when the change affects documented behavior, project structure, or commands.
6. In the final response, summarize the changes, checks performed, results, and remaining limitations. Explicitly identify checks that could not be run and explain why; do not report unverified behavior as verified.
7. Creating a commit is not required to complete a task and still requires the user's separate approval.
