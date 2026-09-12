# vendor/wheels/

Real wheel files for every runtime/verification Python dependency (Flask +
Playwright and their full transitive dependency trees — see
`../requirements.txt`), downloaded from PyPI once, in advance, so
`pip install` needs **zero network access** for the Python side of the
stack:

```
python3 -m pip install --no-index --find-links=vendor/wheels -r requirements.txt
```

**Platform scope, stated plainly**: two of these wheels
(`greenlet`, `markupsafe`) are platform/Python-version-specific compiled
binaries, built here for **Linux x86_64, CPython 3.11** (`cp311`,
`manylinux`). They will not install on a different OS, CPU architecture, or
Python minor version. On any other platform, skip `--no-index` and let pip
resolve normal PyPI wheels for your platform instead:

```
python3 -m pip install -r requirements.txt
```

This directory does **not** include a browser binary for Playwright (that's
a ~300-600MB download, not a Python package — vendoring it here would make
this repository unreasonably large the same way no real project vendors a
browser into its source tree). See `../README.md` for the one remaining
step that needs either network access or an existing Chromium install.
