void gtk_widget_insert_action_group(GtkWidget *Widget, const char *Name,
	GActionGroup *Group) {
	// Entry point used by applications to add actions to a widget under a
	// prefix. Hook it, to keep the group for the stand-ins of the global menu

	GTKNoCSDGetReferences(true);
	if (o_gtk_widget_insert_action_group != NULL) {
		o_gtk_widget_insert_action_group(Widget, Name, Group);
	}

	if (!GTKNoCSDGlobalMenu || GTKNoCSDGTKVersion != 4 || Widget == NULL ||
		Name == NULL) {
		return;
	}
	GTKNoCSDMenuPrepare();
	if (!GTKNoCSDMenuProxyReady) {
		return;
	}

	// Replace or drop the group kept for this widget and prefix
	struct GTKNoCSDMenuGroup *Kept = GTKNoCSDMenuGroups;
	while (Kept != NULL &&
		(Kept->Widget != Widget || strcmp(Kept->Prefix, Name) != 0)) {
		Kept = Kept->Next;
	}
	if (Kept == NULL && Group != NULL) {
		Kept = calloc(1, sizeof(struct GTKNoCSDMenuGroup));
		if (Kept == NULL) {
			return;
		}
		Kept->Widget = Widget;
		o_g_object_add_weak_pointer((GObject *) Widget,
			(gpointer *) &Kept->Widget);
		Kept->Prefix = o_g_strdup(Name);
		Kept->Next = GTKNoCSDMenuGroups;
		GTKNoCSDMenuGroups = Kept;
	}
	if (Kept != NULL) {
		if (Kept->Group != NULL) {
			o_g_object_unref((GObject *) Kept->Group);
		}
		Kept->Group = Group != NULL ?
			(GActionGroup *) o_g_object_ref((GObject *) Group) : NULL;
	}

	// Stand-ins of the window this widget is in follow the change
	for (struct GTKNoCSDMenuGroupProxy *Proxy = GTKNoCSDMenuGroupProxies;
		Proxy != NULL; Proxy = Proxy->Next) {
		if (Proxy->Map != NULL && strcmp(Proxy->Prefix, Name) == 0 &&
			GTKNoCSDMenuIsAncestor((GtkWidget *) Proxy->Map, Widget)) {
			GTKNoCSDMenuGroupBind(Proxy);
		}
	}
}

