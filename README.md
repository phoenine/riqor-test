# rigorpath-api-test

Strict YAML-driven API automation runtime used by RigorPath-generated test repositories.

```bash
python -m rigorpath_api_test validate testcases
pytest
```

The runtime deliberately contains no product endpoints, credentials, branch rules, or environment defaults. Generated business repositories own those values. Network execution is separate from static validation.
