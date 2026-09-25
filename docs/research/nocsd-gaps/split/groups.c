// Actions of groups inserted on a widget (gtk_widget_insert_action_group)
// are not exported either. The hook of gtk_widget_insert_action_group keeps
// every group with its widget and prefix; a stand-in in the window's actions
// takes enabled state, state and parameter type from the group, and activates
// the original from the widget it was inserted on, the way GTK's action muxer
// resolves it. A stand-in is only in the window's actions while a group in
// that window has the action, so items hidden when the action is missing
// stay hidden, as in the application

// A group inserted on a widget, under a prefix
struct GTKNoCSDMenuGroup {
	GtkWidget *Widget;
	gchar *Prefix;
	GActionGroup *Group;
	struct GTKNoCSDMenuGroup *Next;
};
struct GTKNoCSDMenuGroup *GTKNoCSDMenuGroups = NULL;

// A stand-in for an action of an inserted group, in one window
struct GTKNoCSDMenuGroupProxy {
	GActionMap *Map;
	GtkWidget *Holder;
	gchar *Name;
	gchar *Prefix;
	gchar *Action;
	gchar *Local;
	GSimpleAction *StandIn;
	GActionGroup *Group;
	gulong EnabledHandler;
	gulong StateHandler;
	struct GTKNoCSDMenuGroupProxy *Next;
};
struct GTKNoCSDMenuGroupProxy *GTKNoCSDMenuGroupProxies = NULL;

bool GTKNoCSDMenuIsAncestor(GtkWidget *Ancestor, GtkWidget *Widget) {
	// Whether the first widget is the second one or one of its ancestors

	// WARNING: Own call
	for (; Widget != NULL; Widget = gtk_widget_get_parent(Widget)) {
		if (Widget == Ancestor) {
			return true;
		}
	}

	return false;
}

struct GTKNoCSDMenuGroup *GTKNoCSDMenuFindGroup(GActionMap *Map,
	const char *Prefix, const char *Action) {
	// A group inserted in the window under the prefix that has the action

	for (struct GTKNoCSDMenuGroup *Group = GTKNoCSDMenuGroups; Group != NULL;
		Group = Group->Next) {
		if (Group->Widget != NULL && Group->Group != NULL &&
			strcmp(Group->Prefix, Prefix) == 0 &&
			GTKNoCSDMenuIsAncestor((GtkWidget *) Map, Group->Widget) &&
			o_g_action_group_has_action(Group->Group, Action)) {
			return Group;
		}
	}

	return NULL;
}

void GTKNoCSDMenuGroupEnabled(G_GNUC_UNUSED GActionGroup *Group,
	G_GNUC_UNUSED const gchar *Action, gboolean Enabled, gpointer Data) {
	// Follow the enabled state of the original action

	struct GTKNoCSDMenuGroupProxy *Proxy = Data;
	o_g_simple_action_set_enabled(Proxy->StandIn, Enabled);
}

void GTKNoCSDMenuGroupState(G_GNUC_UNUSED GActionGroup *Group,
	G_GNUC_UNUSED const gchar *Action, GVariant *Value, gpointer Data) {
	// Follow the state of the original action

	struct GTKNoCSDMenuGroupProxy *Proxy = Data;
	o_g_simple_action_set_state(Proxy->StandIn, Value);
}

void GTKNoCSDMenuGroupActivate(G_GNUC_UNUSED GSimpleAction *Action,
	GVariant *Parameter, gpointer Data) {
	// Activate the original action from the widget its group is on

	struct GTKNoCSDMenuGroupProxy *Proxy = Data;
	if (Proxy->Holder != NULL) {
		o_gtk_widget_activate_action_variant(Proxy->Holder, Proxy->Name,
			Parameter);
	}
}

void GTKNoCSDMenuGroupChangeState(GSimpleAction *Action, GVariant *Value,
	gpointer Data) {
	// A state change asked over D-Bus goes to the original action like
	// activation. The new state comes back through its signal

	struct GTKNoCSDMenuGroupProxy *Proxy = Data;
	if (Proxy->Holder == NULL) {
		return;
	}

	if (!o_g_variant_is_of_type(Value, G_VARIANT_TYPE_BOOLEAN)) {
		o_gtk_widget_activate_action_variant(Proxy->Holder, Proxy->Name,
			Value);
		return;
	}

	GVariant *Current = o_g_action_get_state((GAction *) Action);
	bool Differs = Current == NULL ||
		o_g_variant_get_boolean(Current) != o_g_variant_get_boolean(Value);
	if (Current != NULL) {
		o_g_variant_unref(Current);
	}
	if (Differs) {
		o_gtk_widget_activate_action_variant(Proxy->Holder, Proxy->Name,
			NULL);
	}
}

void GTKNoCSDMenuGroupBind(struct GTKNoCSDMenuGroupProxy *Proxy) {
	// Bind a stand-in to the group of its window that has its action, or
	// take it out of the window's actions when there is none

	if (Proxy->Group != NULL) {
		o_g_signal_handler_disconnect(Proxy->Group, Proxy->EnabledHandler);
		o_g_signal_handler_disconnect(Proxy->Group, Proxy->StateHandler);
		o_g_object_unref((GObject *) Proxy->Group);
		Proxy->Group = NULL;
	}
	if (Proxy->Holder != NULL) {
		o_g_object_remove_weak_pointer((GObject *) Proxy->Holder,
			(gpointer *) &Proxy->Holder);
		Proxy->Holder = NULL;
	}
	if (Proxy->Map == NULL) {
		return;
	}

	struct GTKNoCSDMenuGroup *Found = GTKNoCSDMenuFindGroup(Proxy->Map,
			Proxy->Prefix, Proxy->Action);
	if (Found == NULL) {
		if (Proxy->StandIn != NULL &&
			o_g_action_map_lookup_action(Proxy->Map, Proxy->Local) ==
			(GAction *) Proxy->StandIn) {
			o_g_action_map_remove_action(Proxy->Map, Proxy->Local);
		}
		return;
	}

	GActionGroup *Group = Found->Group;
	Proxy->Group = (GActionGroup *) o_g_object_ref((GObject *) Group);
	Proxy->Holder = Found->Widget;
	o_g_object_add_weak_pointer((GObject *) Proxy->Holder,
		(gpointer *) &Proxy->Holder);

	GVariant *State = o_g_action_group_get_action_state(Group, Proxy->Action);
	if (Proxy->StandIn == NULL) {
		const GVariantType *Type =
			o_g_action_group_get_action_parameter_type(Group, Proxy->Action);
		Proxy->StandIn = State != NULL ?
			o_g_simple_action_new_stateful(Proxy->Local, Type, State) :
			o_g_simple_action_new(Proxy->Local, Type);
		o_g_signal_connect_data(Proxy->StandIn, "activate",
			(GCallback) GTKNoCSDMenuGroupActivate, Proxy, NULL, 0);
		if (State != NULL) {
			o_g_signal_connect_data(Proxy->StandIn, "change-state",
				(GCallback) GTKNoCSDMenuGroupChangeState, Proxy, NULL, 0);
		}
	} else if (State != NULL) {
		o_g_simple_action_set_state(Proxy->StandIn, State);
	}
	if (State != NULL) {
		o_g_variant_unref(State);
	}
	o_g_simple_action_set_enabled(Proxy->StandIn,
		o_g_action_group_get_action_enabled(Group, Proxy->Action));

	gchar *Signal = o_g_strconcat("action-enabled-changed::", Proxy->Action,
			NULL);
	Proxy->EnabledHandler = o_g_signal_connect_data(Group, Signal,
			(GCallback) GTKNoCSDMenuGroupEnabled, Proxy, NULL, 0);
	o_g_free(Signal);
	Signal = o_g_strconcat("action-state-changed::", Proxy->Action, NULL);
	Proxy->StateHandler = o_g_signal_connect_data(Group, Signal,
			(GCallback) GTKNoCSDMenuGroupState, Proxy, NULL, 0);
	o_g_free(Signal);

	if (o_g_action_map_lookup_action(Proxy->Map, Proxy->Local) == NULL) {
		o_g_action_map_add_action(Proxy->Map, (GAction *) Proxy->StandIn);
	}
}

gchar *GTKNoCSDMenuGroupProxyFor(const char *Name, GActionMap *Map) {
	// The action name the exported item uses for an action that is neither
	// exported nor a class action: a stand-in in the window's actions,
	// otherwise NULL, keep the name

	const char *Dot = strchr(Name, '.');
	if (Map == NULL || Dot == NULL || strncmp(Name, "app.", 4) == 0) {
		return NULL;
	}

	// A window action is exported by GTK, now or once the application adds
	// it. Only a group the application inserted as "win" itself hides the
	// window's own actions (Epiphany)
	if (strncmp(Name, "win.", 4) == 0 &&
		(o_g_action_map_lookup_action(Map, Dot + 1) != NULL ||
		GTKNoCSDMenuFindGroup(Map, "win", Dot + 1) == NULL)) {
		return NULL;
	}

	struct GTKNoCSDMenuGroupProxy *Proxy = GTKNoCSDMenuGroupProxies;
	while (Proxy != NULL &&
		(Proxy->Map != Map || strcmp(Proxy->Name, Name) != 0)) {
		Proxy = Proxy->Next;
	}

	if (Proxy == NULL) {
		Proxy = calloc(1, sizeof(struct GTKNoCSDMenuGroupProxy));
		if (Proxy == NULL) {
			return NULL;
		}
		Proxy->Map = Map;
		o_g_object_add_weak_pointer((GObject *) Map,
			(gpointer *) &Proxy->Map);
		Proxy->Name = o_g_strdup(Name);
		Proxy->Prefix = o_g_strdup(Name);
		Proxy->Prefix[Dot - Name] = '\0';
		Proxy->Action = o_g_strdup(Dot + 1);

		// No dots, the whole name after win. is one action name
		Proxy->Local = o_g_strconcat("gtk-nocsd-", Name, NULL);
		for (gchar *Character = Proxy->Local; *Character != '\0';
			++Character) {
			if (*Character == '.') {
				*Character = '-';
			}
		}

		Proxy->Next = GTKNoCSDMenuGroupProxies;
		GTKNoCSDMenuGroupProxies = Proxy;
		GTKNoCSDMenuGroupBind(Proxy);
	}

	return o_g_strconcat("win.", Proxy->Local, NULL);
}

