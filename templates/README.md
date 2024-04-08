These files are templates defining the standard format across all SciTools
repos. Repo deviations from template are periodically identified in pull
requests by the repo-file-sync-action.

### Possible actions on a deviation pull request

- ✔️ **Merge** - all deviations are re-aligned with the template
  (E.g. the repo is simply out of date and needs updating).
- ❌ **Close** - all deviations are kept
  (E.g. all deviations are required repo-specific detail).
- ️️✏️ **Edit** - re-align some deviations, keep others.
- 🏃 **Close then action independently**
  (E.g. the repo contains content that should be added to the template).

### Further reading

- https://github.com/marketplace/actions/repo-file-sync-action
- [../.github/workflows/template-sync.yml](../.github/workflows/template-sync.yml)
- [../.github/template-sync.yml](../.github/template-sync.yml)