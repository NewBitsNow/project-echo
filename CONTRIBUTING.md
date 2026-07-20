# Contributing to Project Echo

Thanks for your interest in Project Echo! This is a small, focused project and contributions are welcome.

## Guidelines

- **Keep it local-first.** The framework should run entirely on-device. API calls are optional.
- **Consent-first design.** Every agent action should be governed by the consent contract.
- **Zero cost by default.** Prefer local models (Ollama) over API calls. Free tier over paid.
- **Test coverage.** New features need tests. Run `pytest` before submitting.
- **Audit trail.** Every user-facing action should be logged.

## Getting Started

```bash
git clone https://github.com/NewBitsNow/echo-core
cd echo-core
pip install -e ".[dev]"
pytest
```

## Pull Request Process

1. Open an issue describing what you want to change
2. Fork the repo and create a branch
3. Make your changes with tests
4. Run the full test suite
5. Submit a PR with a clear description

## Code Style

- Type hints on all public functions
- Docstrings explaining the "why" not just the "what"
- No external dependencies beyond what's in pyproject.toml
- Paths should be overridable via `set_*_path()` functions