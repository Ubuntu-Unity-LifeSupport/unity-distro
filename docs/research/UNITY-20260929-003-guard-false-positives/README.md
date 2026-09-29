# UNITY-20260929-003 - command_guard false positives (started, paused)

Paused 2026-09-29 ~14:55Z for UNITY-20260927-021 (C). Only preparation was done:
`denials.py` collects every refusal of the guard from the Claude Code transcripts
(read-only). On 2026-09-29 it found 27 refusals, 10 of them "could not parse shell
quoting". The cases C listed: quoted-delimiter heredocs with an apostrophe or
quotes in the body; backtick forms; aptly/publish only inside data strings.
May confirmed the task in B's session b7902aab. No guard change yet.
