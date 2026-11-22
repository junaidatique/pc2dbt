# pc2dbt: PowerCenter mapping XML to dbt

A converter from an Informatica PowerCenter mapping export to a dbt project, with tests.

This README is written in full in build step 4 (how to run, assumptions, what isn't handled, where the
output is likely wrong, the agent's mistakes, prompts, process and time). Until then it lists only the
unknowns found so far.

## Unknowns

Things the converter has to assume because Informatica's documentation doesn't settle them or we
couldn't confirm them. Each one has a test that pins the behaviour we chose, so a change shows up.

| Unknown | What the converter does | Pinned by |
|---|---|---|
| How an Aggregator groups rows whose group-by key is NULL. One Informatica guide (for a different product) says no group is created; a PowerCenter guide mentions "null groups". | SQL's rule: all NULL keys form one group. The jaffle-shop seed has no NULL keys, so the comparison is not affected. | `tests/test_convert_marts_mini.py::test_null_group_keys_form_one_group` |
| Whether `DATE_DIFF(date1, date2, 'DD')` returns fractions of a day. | Exact elapsed days with fractions (12 hours = 0.5). This XML truncates both dates first (L2300, L2318), so its results are whole days either way. | `tests/test_expressions.py::test_date_diff_in_days_keeps_fractions` |
