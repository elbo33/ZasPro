# ZasPro

Polish Matura knowledge base. Read docs/SPEC.md in full before doing
anything; it is the authoritative specification. docs/sources.md holds the
verified source inventory and extraction tooling research.

## Standing rules
- Work one milestone at a time. Stop at the end of each and wait.
- Never touch a later milestone's scope, especially anything under
  "EXPLICITLY OUT OF SCOPE" in the spec.
- Record architectural decisions as short ADRs in docs/decisions/.
- Ask before adding a dependency that brings infrastructure with it.
- Files in sources/raw/ are read-only source material. Do not process
  them beyond what the current milestone requires.