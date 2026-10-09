# Phase 3: ask and deny rules under `bypassPermissions` (measurement record)

The sessions on this machine run `--permission-mode bypassPermissions`
(desktop app, ccd-cli 2.1.284; the CLI on PATH is 2.1.278). The permissions
block of phase 3 relies on `ask` rules producing a prompt and `deny` rules
holding in that mode. Both were measured, not assumed, with throwaway
`claude -p` sessions (model `claude-haiku-4-5-20251001`, `--output-format
json`) and a throwaway `--settings` file. The live `~/.claude/settings.json`
was never changed; in `-p` mode a prompt cannot be answered, so an `ask`
shows up as a `permission_denials` entry and the step does not run.

## Run 1 (2026-10-09 12:09Z): Bash ask rule and hook ask decision

Settings: `permissions.ask = ["Bash(echo probe-ask*)"]` plus a PreToolUse
hook returning `permissionDecision: "ask"` for a command containing
`probe-hook`. Command:

```
claude -p --model claude-haiku-4-5-20251001 --permission-mode bypassPermissions --settings ./probe-settings.json --output-format json "<three echo steps>"
```

Result: `permission_denials` = `Bash echo probe-ask-2` (the ask rule) and
`Bash echo probe-hook-3` (the hook decision); the control command without
a rule ran. Control session without `--settings`: no denials, all three ran.
Same prompt under `--permission-mode default`: the same two entries.

## Run 2 (2026-10-09 15:59Z): Edit, Write and Read path rules

Settings (paths under the session scratchpad, abbreviated `<probe>`):

```
deny: Read(//<probe>/secret.txt)
ask:  Edit(//<probe>/edit-only.txt), Write(//<probe>/write-only.txt)
```

Five steps, each with the named tool, in one fresh session
(`020c9724-c5e8-49c8-9f1a-b268c46ac6cd`):

| Step | Tool | Rule on the path | Outcome |
|------|------|------------------|---------|
| 1 | Write `<probe>/edit-only.txt` | `Edit(path)` ask | refused: "requested permissions to write ... but you haven't granted it yet" (`permission_denials`: Write) |
| 2 | Write `<probe>/write-only.txt` | `Write(path)` ask | **written**, no prompt (file present afterwards) |
| 3 | Edit `<probe>/write-only-existing.txt` | none | refused by the tool's own read-first rule; not a permission result |
| 4 | Read `<probe>/secret.txt` | `Read(path)` deny | refused: "File is in a directory that is denied by your permission settings" (`permission_denials`: Read) |
| 5 | Bash `cat <probe>/secret.txt` | `Read(path)` deny | refused: "Permission to use Bash with command cat ... has been denied" (`permission_denials`: Bash) |

Conclusions, matching the documentation ("Configure permissions", Read and
Edit): under `bypassPermissions` an `Edit(path)` ask rule stops the Write
tool, a `Write(path)` rule is never consulted, a `Read(path)` deny rule
stops the Read tool and the recognised file commands in Bash. The proposal
therefore carries `Edit` rules only, and `Read(//home/claude/.claude/.credentials.json)`
in `deny`.

Artifacts: session scratchpad `p3-measure/` (run 1) and `p3-measure-2/`
(run 2: `probe-settings.json`, `run.sh`, `run-bypass.json`).
