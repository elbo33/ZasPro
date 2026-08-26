"""Idempotent seeding of the curriculum tree and the source inventory.

`python -m zaspro.seeding.run` loads the hand-verified M0.6 curriculum seed and
`sources/MANIFEST.md`. Re-running it is a no-op (SPEC M1). Licensing metadata is
taken verbatim from the manifest — never generated or inferred.
"""
