# Contributing

1. Create a branch for a focused change.
2. Use synthetic PDF fixtures and mocked model/mail services; never include personal data.
3. Keep Chinese, English, Japanese and Korean UI strings in sync. Do not overwrite user-authored content when changing interface language.
4. Run `python tools/run_tests.py` and `python tools/check_release.py`.
5. For UI changes, verify the actual desktop and mobile views and the affected interactions.
6. Describe the problem, resulting behavior and validation in the pull request.

New dependencies require license and deployment review. Contributions are distributed under AGPL-3.0-only unless an existing third-party file retains a different license.
