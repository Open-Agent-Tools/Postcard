## Summary

<!-- One or two sentences on what changed and why. -->

## Test plan

- [ ] `uv run ruff check src tests`
- [ ] `uv run ruff format --check src tests`
- [ ] `uv run mypy src`
- [ ] `uv run pytest`
- [ ] If this touches a hook, manually verified with
      `env -i HOME=$HOME PATH=/usr/bin:/bin bash ./scripts/<hook>.sh`.

## Notes for reviewers
