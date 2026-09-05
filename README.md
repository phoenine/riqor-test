# rigor-test

Project-agnostic API and Web test runtimes used by RigorPath-generated test repositories.

The repository keeps both runtimes in the existing `src/` layout:

```text
src/
  rigorpath_api_test/
  rigorpath_web_test/
```

## API test runtime

```bash
python -m rigorpath_api_test validate testcases
pytest
```

## Web test runtime

Install the Web dependencies and Playwright browser:

```bash
pip install -e '.[test,web]'
playwright install chromium
```

Use the automatically registered pytest fixtures in a generated business repository:

```python
import pytest


@pytest.mark.rigor_source(
    automation_id="AUTO-001",
    requirements=["REQ-001"],
    test_points=["TP-001"],
    test_cases=["TC-001"],
)
def test_checkout_opens(web_page, webtest_config):
    web_page.goto(webtest_config.base_url)
    web_page.get_by_role("heading", name="Checkout").wait_for()
```

Configure the target without embedding product values in the runtime:

```bash
WEBTEST_BASE_URL=https://example.test pytest
# or
pytest --web-base-url=https://example.test
```

`web_page` records screenshots, redacted URL metadata, browser console messages,
and page errors when setup, call, or teardown fails. Custom pages can opt in with
`web_observer.observe(page)`.

Override the session-scoped `web_storage_state` fixture in the business repository
to reuse authenticated Playwright storage state. The runtime creates a fresh browser
context for every testcase. Web cases using runtime fixtures must declare a valid
`rigor_source` marker with `AUTO`, `TP`, and `TC` traceability.

The runtime validates this metadata during collection. Missing or malformed
traceability fails collection before a browser or target environment is contacted.
The `web_context` fixture is created through pytest-playwright's managed
`new_context`, so native `--tracing`, `--video`, `--screenshot`, device, locale,
and browser-context marker options remain available.

The runtimes deliberately contain no product endpoints, credentials, selectors,
branch rules, or environment defaults. Generated business repositories own those
values. Agent-facing authoring Skills live in Agent-next, not in this runtime
repository.
