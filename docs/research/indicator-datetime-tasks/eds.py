#!/usr/bin/python3
"""eds.py tasks|calendar ICS-FILE  - add a VTODO/VEVENT to the local system task list or calendar
   eds.py clear tasks|calendar     - remove every object from it"""
import sys, gi
gi.require_version('EDataServer', '1.2'); gi.require_version('ECal', '2.0'); gi.require_version('ICalGLib', '3.0')
from gi.repository import EDataServer, ECal, ICalGLib
reg = EDataServer.SourceRegistry.new_sync(None)
def client(kind):
    if kind == 'tasks':
        return ECal.Client.connect_sync(reg.ref_builtin_task_list(), ECal.ClientSourceType.TASKS, 30, None)
    return ECal.Client.connect_sync(reg.ref_builtin_calendar(), ECal.ClientSourceType.EVENTS, 30, None)
if sys.argv[1] == 'clear':
    c = client(sys.argv[2])
    ok, objs = c.get_object_list_sync('#t', None)
    for o in objs:
        c.remove_object_sync(o.get_uid(), None, ECal.ObjModType.ALL, ECal.OperationFlags.NONE, None)
    print('removed', len(objs))
else:
    c = client(sys.argv[1])
    comp = ICalGLib.Component.new_from_string(open(sys.argv[2]).read())
    ok, uid = c.create_object_sync(comp, ECal.OperationFlags.NONE, None)
    print('created', uid)
