# GitHub Codex Review

PR: local://guide

Findings:
- [high] scripts/sync_public_guide_from_design.py [correctness] manifest-generated-from-windows-path-not-normalized
`_render_manifest()` only looks for the literal marker `products/chummer/`, so it leaves `generated_from` unchanged when the manifest contains backslashes (for example `C:\\work\\chummer-design\\products\\chummer\\PUBLIC_GUIDE_EXPORT_MANIFEST.yaml`).; Reproduced locally by calling `_render_manifest()` with a Windows-style `generated_from`; the output remained `C:\\work\\chummer-design\\products\\chummer\\PUBLIC_GUIDE_EXPORT_MANIFEST.yaml` instead of the intended repo-relative `products/chummer/...`.; The new test only covers a POSIX absolute path, so this portability boundary is currently untested and the review feedback fix is not actually complete.
Expected fix: Normalize both `/` and `\\` path variants (or use path-aware logic that strips everything before `products/chummer` regardless of separator), and add a test covering the Windows-style manifest path.
