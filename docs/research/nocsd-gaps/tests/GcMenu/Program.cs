var app = Adw.Application.New("org.test.GcMenu", Gio.ApplicationFlags.DefaultFlags);
var quit = Gio.SimpleAction.New("quit", null);
quit.OnActivate += (_, _) => app.Quit();
app.AddAction(quit);
app.OnActivate += (_, _) => {
    var win = Gtk.ApplicationWindow.New(app);
    win.Title = "GirCore menu test"; win.SetDefaultSize(500, 350);
    var about = Gio.SimpleAction.New("about", null);
    about.OnActivate += (_, _) => { System.Console.WriteLine("ACTIVATED win.about"); };
    win.AddAction(about);
    var menu = Gio.Menu.New(); var sec = Gio.Menu.New();
    sec.Append("About", "win.about"); menu.AppendSection(null, sec); menu.Append("Quit", "app.quit");
    var btn = Gtk.MenuButton.New(); btn.SetIconName("open-menu-symbolic"); btn.SetMenuModel(menu); btn.SetPrimary(true);
    var hb = Gtk.HeaderBar.New(); hb.PackEnd(btn); win.SetTitlebar(hb);
    win.SetChild(Gtk.Label.New("Hello")); win.Present();
};
return app.RunWithSynchronizationContext(null);
