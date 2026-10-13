#!/usr/bin/env python3
"""dbgpatch.py FILE - the debug build of UNITY-20260927-034 for the hidden-button count: one fprintf where
GTKNoCSDMenuClean skips an item that embeds a custom widget. Works for our series and for b76f3fb (the skip is
`if (Custom != NULL) { o_g_variant_unref(Custom); continue; }` in both)."""
import re
import sys

path = sys.argv[1]
src = open(path).read()
old = re.compile(r'(if \(Custom != NULL\) \{\n(\s*)o_g_variant_unref\(Custom\);\n)(\s*continue;)')
new, n = old.subn(lambda m: m.group(1) + m.group(2)
                  + 'fprintf(stderr, "GTK-NoCSD-DROPPED-CUSTOM pid %d item %d\\n", (int) getpid(), (int) Index);\n'
                  + m.group(3), src)
if n != 1:
    sys.exit(f"{path}: expected one custom skip, found {n}")
if '#include <unistd.h>' not in new:
    # after the file's own includes, so its _GNU_SOURCE comes first
    last = max(m.end() for m in re.finditer(r'^#include <[^>]+>\n', new, re.M))
    new = new[:last] + '#include <unistd.h>\n' + new[last:]
open(path, 'w').write(new)
print(f"{path}: patched")
