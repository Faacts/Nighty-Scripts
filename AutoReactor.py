@nightyScript(
    name="Auto Reactor UI",
    author="Factz",
    description="Auto-react (emoji reaction) to all messages from a target user in a target server, optional channel filters.",
    usage="<p>autoreact help"
)
def script_function():
    """
    AUTO REACTOR UI
    ---------------
    Adds an emoji reaction to every qualifying message from the target user.

    COMMANDS:
    <p>autoreact help | status | on | off
    """

    import json
    from pathlib import Path

    JSON_DIR = Path(getScriptsPath()) / "json"
    SETTINGS_FILE = JSON_DIR / "auto_reactor_settings.json"

    DEFAULT_SETTINGS = {
        "enabled": True,
        "target_user_id": "",
        "target_guild_id": "",
        "channel_allowlist": [],
        "emoji_markdown": "👍",
        "ignore_bots": True,
    }

    def ensure_json_dir():
        JSON_DIR.mkdir(parents=True, exist_ok=True)

    def load_settings():
        ensure_json_dir()
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    return DEFAULT_SETTINGS.copy()
                merged = DEFAULT_SETTINGS.copy()
                merged.update(data)
                merged["channel_allowlist"] = [str(x) for x in merged.get("channel_allowlist", [])]
                return merged
        except (FileNotFoundError, json.JSONDecodeError):
            return DEFAULT_SETTINGS.copy()

    def save_settings(data):
        ensure_json_dir()
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    settings = load_settings()

    def persist():
        save_settings(settings)

    def channel_list_text():
        if not settings["channel_allowlist"]:
            return "No channel filters set (all channels in target server are allowed)."
        return "Allowed channels:\n" + "\n".join([f"- {cid}" for cid in settings["channel_allowlist"]])

    @bot.command(name="autoreact", description="Auto reactor controls")
    async def autoreact_cmd(ctx, *, args: str = ""):
        await ctx.message.delete()
        parts = args.strip().split()

        if not parts or parts[0].lower() == "help":
            await ctx.send(
                "**Auto Reactor**\n"
                "`autoreact status` | `autoreact on` | `autoreact off`\n"
                "Configure in **AutoReactorUI** tab."
            )
            return

        sub = parts[0].lower()

        if sub == "status":
            await ctx.send(
                f"Enabled: `{settings['enabled']}`\n"
                f"Target User: `{settings['target_user_id'] or 'not set'}`\n"
                f"Target Server: `{settings['target_guild_id'] or 'not set'}`\n"
                f"Reaction emoji: `{settings['emoji_markdown']}`\n"
                f"Channel filters: `{len(settings['channel_allowlist'])}`"
            )
            return

        if sub == "on":
            settings["enabled"] = True
            persist()
            await ctx.send("Auto reactor enabled.")
            return

        if sub == "off":
            settings["enabled"] = False
            persist()
            await ctx.send("Auto reactor disabled.")
            return

        await ctx.send("Unknown subcommand. Use `autoreact help`.")

    @bot.listen("on_message")
    async def auto_react_listener(message):
        if message.author.id == bot.user.id:
            return
        if settings.get("ignore_bots", True) and getattr(message.author, "bot", False):
            return
        if not settings.get("enabled", True):
            return

        if not settings["target_guild_id"]:
            return

        guild_id = getattr(getattr(message, "guild", None), "id", None)
        if not guild_id or str(guild_id) != settings["target_guild_id"]:
            return

        if not settings["target_user_id"]:
            return
        if str(message.author.id) != settings["target_user_id"]:
            return

        if settings["channel_allowlist"]:
            if str(message.channel.id) not in settings["channel_allowlist"]:
                return

        emoji = (settings.get("emoji_markdown") or "").strip()
        if not emoji:
            return

        try:
            await message.add_reaction(emoji)
        except Exception as e:
            print(f"Auto react failed: {e}", type_="ERROR")

    tab = Tab(name="AutoReactorUI", icon="star", title="Auto Reactor")
    root = tab.create_container(type="columns", gap=6)

    left = root.create_card(type="rows", width="full", gap=6)
    left.create_ui_element(UI.Text, content="Auto Reactor", size="xl", weight="bold")
    left.create_ui_element(
        UI.Text,
        content="Reacts to every message from one user in one server (optional channels).",
        size="sm",
    )

    enabled_toggle = left.create_ui_element(
        UI.Toggle,
        label="Enabled",
        checked=bool(settings["enabled"]),
    )

    ignore_bots_toggle = left.create_ui_element(
        UI.Toggle,
        label="Ignore bot messages",
        checked=bool(settings["ignore_bots"]),
    )

    user_input = left.create_ui_element(
        UI.Input,
        label="Target User ID",
        value=settings["target_user_id"],
        placeholder="123456789012345678",
        full_width=True,
    )

    guild_input = left.create_ui_element(
        UI.Input,
        label="Target Server (Guild) ID",
        value=settings["target_guild_id"],
        placeholder="123456789012345678",
        description="Required.",
        full_width=True,
    )

    emoji_input = left.create_ui_element(
        UI.Input,
        label="Reaction (unicode or <:name:id>)",
        value=settings["emoji_markdown"],
        placeholder="👍  or  <:name:123456789012345678>",
        description="This is passed to message.add_reaction(). Custom emojis must be usable by your account.",
        full_width=True,
    )

    save_btn = left.create_ui_element(UI.Button, label="Save Settings", variant="cta", full_width=True)

    right = root.create_card(type="rows", width="full", gap=6)
    right.create_ui_element(UI.Text, content="Optional Channel Filters", size="lg", weight="bold")

    channel_input = right.create_ui_element(
        UI.Input,
        label="Channel ID",
        placeholder="123456789012345678",
        description="Leave empty = all channels in target server.",
        full_width=True,
    )

    channel_group = right.create_group(type="columns", gap=4, full_width=True)
    add_channel_btn = channel_group.create_ui_element(UI.Button, label="Add Channel", variant="solid")
    remove_channel_btn = channel_group.create_ui_element(UI.Button, label="Remove Channel", variant="bordered")
    clear_channels_btn = channel_group.create_ui_element(
        UI.Button, label="Clear All", variant="ghost", color="danger"
    )

    channels_text = right.create_ui_element(
        UI.Text,
        content=channel_list_text(),
        size="sm",
    )

    def sync_from_ui():
        settings["enabled"] = bool(enabled_toggle.checked)
        settings["ignore_bots"] = bool(ignore_bots_toggle.checked)
        settings["target_user_id"] = (user_input.value or "").strip()
        settings["target_guild_id"] = (guild_input.value or "").strip()
        settings["emoji_markdown"] = (emoji_input.value or "").strip() or "👍"

    async def on_save():
        sync_from_ui()
        persist()
        channels_text.content = channel_list_text()
        tab.toast(title="Saved", description="Settings updated.", type="SUCCESS")

    async def on_add_channel():
        raw = (channel_input.value or "").strip()
        if not raw.isdigit():
            tab.toast(title="Invalid ID", description="Channel ID must be numeric.", type="ERROR")
            return
        if raw not in settings["channel_allowlist"]:
            settings["channel_allowlist"].append(raw)
            persist()
            channels_text.content = channel_list_text()
            tab.toast(title="Added", description=f"Channel {raw} added.", type="SUCCESS")
        else:
            tab.toast(title="Exists", description="Channel already in list.", type="INFO")

    async def on_remove_channel():
        raw = (channel_input.value or "").strip()
        if raw in settings["channel_allowlist"]:
            settings["channel_allowlist"].remove(raw)
            persist()
            channels_text.content = channel_list_text()
            tab.toast(title="Removed", description=f"Channel {raw} removed.", type="SUCCESS")
        else:
            tab.toast(title="Not Found", description="Channel ID is not in list.", type="ERROR")

    async def on_clear_channels():
        settings["channel_allowlist"] = []
        persist()
        channels_text.content = channel_list_text()
        tab.toast(title="Cleared", description="All channel filters removed.", type="SUCCESS")

    save_btn.onClick = on_save
    add_channel_btn.onClick = on_add_channel
    remove_channel_btn.onClick = on_remove_channel
    clear_channels_btn.onClick = on_clear_channels

    tab.render()


script_function() 