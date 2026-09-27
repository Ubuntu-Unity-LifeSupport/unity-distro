---
name: vbox-recovery
description: Restore an assigned disposable VM or coordinate recovery after a suspected shared VirtualBox/VBoxSVC failure.
---

# VBox recovery

Agents may freely change, reboot, power off, restore, and experiment inside
their assigned disposable test VM. Do not add task-board, evidence, role, or
approval gates to routine operations on that VM. Agent A owns `target-desktop`,
agent B owns `target-desktop-2`; `oem-test` needs an explicit task assignment.
Use the full VM name.

## Planned restore

1. Shut down the guest cleanly with its SSH session or `guest_shutdown_ssh`.
2. Wait until VirtualBox reports the VM powered off; check that the VBox server
   still responds.
3. Issue one `restore_snapshot` call and wait for it to finish. Do not repeat
   an ambiguous or failed restore.
4. Boot the VM and verify a fresh boot, expected package versions, and (for a
   clean rollback) that `~/.dirty` is absent. A `current_snapshot` value alone
   does not prove the restore completed.

## Suspected shared backend failure

Treat VBoxSVC hangs, a backend crash, `list_vms` failures, or an ambiguous
restore timeout as a shared-host incident, not a guest-only problem:

- Stop VBox calls from all sessions, including calls for other VMs.
- Do not retry the restore, kill or restart VBoxSVC/VirtualBox, or reboot the
  builder. The builder runs inside the same VirtualBox host.
- Notify the coordinator, May, and the other VM operator with the exact failed
  call and observed error.
- Once the backend responds again, inspect `server_status`, `list_vms`, and the
  affected VM's state before deciding on one recovery action.

This protocol coordinates access to shared host infrastructure. It is not an
ACL on an agent's disposable VM. See `docs/TWO-AGENTS.md` for machine ownership
and coordination details.
