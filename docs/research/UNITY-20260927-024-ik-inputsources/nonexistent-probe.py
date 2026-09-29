import gi, sys
gi.require_version("AccountsService", "1.0")
from gi.repository import AccountsService, GLib
m = AccountsService.UserManager.get_default()
loop = GLib.MainLoop()
def go():
    for name in sys.argv[1:]:
        u = m.get_user(name)
        def rep(u, p=None, name=name):
            if u.is_loaded():
                s = u.get_input_sources()
                print(name, "loaded=True nonexistent=%s name=%r input_sources=%s" % (u.props.nonexistent, u.get_user_name(), "NULL" if s is None else s.print_(False)), flush=True)
        if u.is_loaded(): rep(u)
        else: u.connect("notify::is-loaded", rep)
    GLib.timeout_add(3000, loop.quit)
def ml(*_):
    if m.props.is_loaded: go()
if m.props.is_loaded: go()
else: m.connect("notify::is-loaded", ml)
loop.run()
