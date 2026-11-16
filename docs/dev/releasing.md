# Releasing

## Branches

`develop` is the default and PR branch; `main` is the release branch. Work on a
feature branch named after the GitHub issue and open a PR into `develop`.

## Versioning

The version appears in three places and they move together:

- `VERSION`
- `version` in `pyproject.toml`
- a new section at the top of `CHANGELOG.rst`, with one bullet per user-visible change
  and the issue number in parentheses where there is one

## Release

```bash
make release VERSION=1.2.3 [RELEASE_TITLE="..."]
```

Downloads the release script from `sowwic/gh-workflows` (pinned by `GH_WORKFLOWS_REF`,
default `v1`), which tags `main` and merges it back into `develop`.
`RELEASE_BRANCH` and `DEVELOP_BRANCH` override the branch names.

## CI

The workflows in `.github/workflows/` are thin callers of the shared workflows in
`sowwic/gh-workflows`: unit tests, code quality, docs deployment and release. Docs
are built with MkDocs (`mkdocs.yml`), so a docstring that breaks `mkdocstrings`
fails the docs build.
