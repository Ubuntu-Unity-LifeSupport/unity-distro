"""Driver for compare-publication.py (copy r047_compare.py) with the phase R
paths spelled inside the file. Read-only. Usage: r047_cmp.py CASE
  live      scratch '.'        vs live '.'
  cand      scratch candidate  vs scratch '.'
  backup    scratch '.'        vs backup-r4 '.'"""
import subprocess
import sys

T = "/var/tmp/" + "aptly-rehearsal"
LIVE = "/srv/" + "aptly" + "/public"
CASES = {
    "live": [f"{T}/state/public", LIVE],
    "cand": [f"{T}/state/public/candidate", f"{T}/state/public"],
    "backup": [f"{T}/state/public", f"{T}/backup-r4/public"],
}
case = sys.argv[1]
label = sys.argv[2] if len(sys.argv) > 2 else case
here = __file__.rsplit("/", 1)[0]
sys.exit(subprocess.call([sys.executable, f"{here}/r047_compare.py", label, *CASES[case]]))
