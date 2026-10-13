# Ask calibration (May, 2026-10-09)

May's principle: a simple system with a few accepted risks over a prompt at
every step; the hook is a safety net for significant risks, not a universal
blocker; no HTTP analyser.

## Measurement

Every distinct Bash command (11 468) and Edit/Write target (1 151) of the
agents' transcripts on builder, matched against the live block with Claude
Code's prefix semantics (scratchpad `ask_calibration.py`): the ask rules
would have fired 25 times, all on real external changes (`gh repo create`
13, `gh repo edit` 10, `gh api -X DELETE` 2), plus once on my own P3 probe
`sudo usermod --help`. No Edit/Write of the agents touched a trusted file.
Fresh-session probes (haiku, bypassPermissions, throwaway `--settings`):
`curl -X GET` and `gh api -X GET` are asked by the live block; prefix rules
are case-sensitive and need the prefix followed by a space at the start of
the command (`printf -X DELETE a` asked, `-X delete`, `-X Delete`,
`-XDELETE`, `-s -X DELETE` ran). `gh api` accepts a method in any case
(`get`, `GET`, `Get` all read `rate_limit`).

## Change (this record's commit)

The four broad rules `Bash(curl -X *)`, `Bash(curl --request *)`,
`Bash(gh api -X *)`, `Bash(gh api --method *)` become method-specific:
`POST`, `PUT`, `PATCH`, `DELETE` and their lower-case spellings, with `-X`
and `--request` / `--method`: 32 rules for 4; the block goes from 94 to 122
ask rules. GET, named or default, no longer asks. The data, form and upload
options (`-d/--data*/-F/--form/-T/--upload-file`, `wget --post-*`,
`gh api -F/-f/--field/--raw-field/--input`) and every deny rule are
unchanged.

## Accepted residual (not to be closed by an analyser)

- Mixed-case methods (`curl -X Delete`, `gh api -X Delete`) do not ask:
  deliberately left outside the rules for simplicity; `gh` would execute
  them.
- Glued and reordered spellings (`curl -XPOST`, `curl -s -X POST`,
  `gh api -XDELETE`) do not ask; they were outside the broad rules too and
  are not extended here.
- `sudo usermod --help` (and `useradd`, `passwd -S`, `chpasswd --help`)
  asks: prefix rules have no exceptions and `allow` never overrides `ask`;
  listing the changing flags would open real changes. One prompt on a
  reference call that the agents never made.

The live `~/.claude/settings.json` is unchanged by this commit; applying
the new block is May's separate GO (`--propose`, the Write tool, `--check`),
as in phase 3.

## Rollout (2026-10-10, May's GO)

Merged into `main` c969589 (fast-forward; installer and guard suites 55 OK
from the base checkout). The proposal was regenerated from `main`: the diff
against the live file was exactly the four broad rules removed and the 32
method-specific rules added (deny, hooks and the other keys identical;
94 -> 122 ask rules). Backup `~/.claude/settings.json.bak-ask-calibration-20261010`
(byte-identical to the previous live file, sha256 b57fe064...), then the
proposal written over `~/.claude/settings.json` with the Write tool
(sha256 6ee02eb0...); live byte-identical to the proposal, block equal to
`PERMISSIONS`, `settings_problems` empty, `--check` OK.

Acceptance on the live settings (fresh haiku sessions, bypassPermissions):

| Probe | Outcome |
|-------|---------|
| `curl -X GET https://example.invalid/` | ran (DNS failure of the invalid host) |
| `gh api -X GET rate_limit` | ran |
| `curl -X POST …`, `curl -X delete …` | asked |
| `gh api -X DELETE rate_limit`, `gh api --method post rate_limit` | asked |
| `curl -d a=b …` | asked (unchanged) |
| `aptly publish list` | refused (guard text; the deny rule stands behind it) |
| `git push --force origin zzz-nonexistent-branch` | refused |

Accepted limits, restated: mixed-case, glued (`-XPOST`) and reordered
(`-s -X POST`) method spellings are outside the rules, deliberately, for
simplicity; `sudo usermod --help` asks. No analyser is added for them.
