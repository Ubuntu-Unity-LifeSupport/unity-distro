#!/usr/bin/env python3
"""usage-rows.py - hud's usage table (~/.cache/indicator-appmenu/hud-usage-log.sqlite) with each row's
timestamp: which application id a use was recorded under, and when."""
import os
import sqlite3

db = sqlite3.connect(os.path.expanduser('~/.cache/indicator-appmenu/hud-usage-log.sqlite'))
cols = [r[1] for r in db.execute("pragma table_info(usage)")]
print("columns:", cols)
for row in db.execute("select * from usage order by rowid"):
    print(row)
