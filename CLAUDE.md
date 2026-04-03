# Financial News Sentiment Analyzer

Streamlit app that fetches financial news from Google News RSS, classifies sentiment with OpenAI (`gpt-4o-mini`), and emails a report via Gmail SMTP.

## Package Management

This project uses **uv**. Do not use pip or manually manage `.venv`.

```bash
# Install / sync dependencies
uv sync

# Add a new dependency
uv add <package>

# Remove a dependency
uv remove <package>
```

Dependencies are declared in `pyproject.toml`. The lockfile is `uv.lock`.

## Git Conventions

- All commit messages, PR titles, and descriptions must be in English.
- Use [Conventional Commits](https://www.conventionalcommits.org/) format:

  | Prefix | When to use | Version bump |
  | --- | --- | --- |
  | `fix:` | Bug fixes | patch |
  | `feat:` | New features | minor |
  | `feat!:` / `BREAKING CHANGE` footer | Incompatible changes (removed feature, changed CLI args, switched API provider) | major |
  | `docs:`, `chore:`, `refactor:`, `test:` | Everything else | none |

- Run `./bump-version.sh` to auto-tag based on commits since the last tag.

## Documentation

When making changes that affect usage, setup, workflow, or features, update `README.md` before committing.
