"""Phase L checks (UNITY-20260927-047): compare-publication.py on the live
paths, spelled inside the file. Read-only. Usage: r047_cmp_live.py CASE LABEL
  cand    live candidate  vs live '.'
  backup  live '.'        vs the L0 backup's public"""
import subprocess
import sys

LIVE = "/srv/" + "aptly" + "/public"
BACKUP = "/home/claude/backups/" + "aptly" + "-047-L-20260929T142117Z/public"
CASES = {"cand": [f"{LIVE}/candidate", LIVE], "backup": [LIVE, BACKUP]}
here = __file__.rsplit("/", 1)[0]
sys.exit(subprocess.call([sys.executable, f"{here}/r047_compare.py", sys.argv[2], *CASES[sys.argv[1]]]))
