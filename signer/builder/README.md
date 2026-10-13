# builder-side units of the aptly-signer (permission model phase 5)

`aptly-signer-refresh.service` and `.timer`: the cadence refresh
(`scripts/signer_client.py refresh --task cadence --current`) every 12 h.
May installs them as user units of `claude` and enables linger; the
signer VM runs its own `resign` timer at the same cadence (both well inside
`valid_days` 3). The timers are installed last in the cut-over (runbook
step 5 of `docs/research/permission-model-2026-10-09/phase5-signer-routine-policy.md`):
until then the re-sign of the adopted content is May's manual step.
