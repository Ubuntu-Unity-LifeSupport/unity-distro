import sys
p = sys.argv[1]
s = open(p).read()
a = '''    results = []
    if not gnote:
        return results
    if search:
    	gnote_search = gnote.SearchNotes('(sb)', search, False)
    else:
        gnote_search = gnote.ListAllNotes()
'''
b = '''    results = []
    if not gnote:
        return results
    # Gnote is started by D-Bus activation on the first call and registers
    # its RemoteControl object only once it is up, so the first calls fail
    # with UnknownMethod; retry for up to three seconds
    for attempt in range(15):
        try:
            if search:
                gnote_search = gnote.SearchNotes('(sb)', search, False)
            else:
                gnote_search = gnote.ListAllNotes()
            break
        except GLib.Error as error:
            if attempt == 14:
                print(error)
                return results
            time.sleep(0.2)
'''
assert s.count(a) == 1, 'search block'
s = s.replace(a, b)
if '\nimport time\n' not in s:
    s = s.replace('\nimport datetime\n', '\nimport datetime\nimport time\n', 1)
assert '\nimport time\n' in s
open(p, 'w').write(s)
