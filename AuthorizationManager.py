import asyncio
import requests
import json
import os

@nightyScript(
    name="Authorization Manager",
    author="Factz",
    description="Manage authorized apps on your Discord account.",
    usage="<p>authlist | <p>deauth <auth_id(s)|all> | <p>authwl add/remove <app_id(s)|all>"
)
def AuthScript():

    CONFIG_PATH = os.path.join(os.environ["APPDATA"], "Nighty Selfbot", "nighty.config")

    def get_token():
        try:
            with open(CONFIG_PATH, "r") as f:
                config = json.load(f)
            for login in config.get("logins", {}).values():
                if login.get("active"):
                    return login.get("token", "")
        except Exception as e:
            print(f"[Auth] Config read failed: {e}", type_="ERROR")
        return ""

    async def run_in_thread(func, *args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    def fetch_authorized_apps(token):
        r = requests.get(
            "https://discord.com/api/v10/oauth2/tokens",
            headers={"Authorization": token}
        )
        if r.status_code == 200:
            return r.json()
        return None

    def revoke_app(token, auth_id):
        r = requests.delete(
            f"https://discord.com/api/v10/oauth2/tokens/{auth_id}",
            headers={"Authorization": token}
        )
        return r.status_code == 204

    WHITELIST_KEY = "auth_whitelist"

    def get_whitelist():
        raw = getConfigData().get(WHITELIST_KEY, "")
        if not raw:
            return []
        return raw.split(",")

    def save_whitelist(wl):
        updateConfigData(WHITELIST_KEY, ",".join(wl))

    @bot.command(name="authlist", description="List all authorized apps.")
    async def authlist(ctx):
        await ctx.message.delete()
        token = get_token()
        if not token:
            await ctx.send("Could not read token from config.", silent=True)
            return

        apps = await run_in_thread(fetch_authorized_apps, token)
        if not apps:
            await ctx.send("Failed to fetch authorized apps.", silent=True)
            return

        whitelist = get_whitelist()
        whitelisted = []
        unwhitelisted = []

        for app in apps:
            app_data = app.get("application", {})
            app_id = app_data.get("id", "?")
            name = app_data.get("name", "Unknown")
            line = f"* {name} | ||{app_id}||"
            if app_id in whitelist:
                whitelisted.append(line)
            else:
                unwhitelisted.append(line)

        msg = ""
        if whitelisted:
            msg += "**WHITELISTED**\n"
            msg += "\n".join(whitelisted)
            msg += f"\n-# {len(whitelisted)} whitelisted apps\n\n"
        if unwhitelisted:
            msg += "**UNWHITELISTED**\n"
            msg += "\n".join(unwhitelisted)
            msg += f"\n-# {len(unwhitelisted)} unwhitelisted apps"

        await ctx.send(msg, silent=True)

    @bot.command(name="deauth", description="Revoke specific apps or all non-whitelisted apps.")
    async def deauth(ctx, *, target: str = ""):
        await ctx.message.delete()
        if not target:
            await ctx.send("Usage: `<p>deauth <auth_id(s)|all>`", silent=True)
            return

        token = get_token()
        if not token:
            await ctx.send("Could not read token from config.", silent=True)
            return

        targets = target.strip().split()

        if len(targets) == 1 and targets[0].lower() == "all":
            apps = await run_in_thread(fetch_authorized_apps, token)
            if not apps:
                await ctx.send("Failed to fetch authorized apps.", silent=True)
                return

            whitelist = get_whitelist()
            revoked_lines = []
            skipped = 0

            for app in apps:
                app_id = app.get("application", {}).get("id")
                auth_id = app.get("id")
                name = app.get("application", {}).get("name", "Unknown")

                if app_id in whitelist:
                    skipped += 1
                    continue

                success = await run_in_thread(revoke_app, token, auth_id)
                if success:
                    revoked_lines.append(f"* {name} | ||{app_id}||")

                await asyncio.sleep(0.5)

            if not revoked_lines:
                await ctx.send(f"Nothing to deauth. {skipped} whitelisted apps remaining.", silent=True)
            else:
                msg = "Successfully unauthorized:\n"
                msg += "\n".join(revoked_lines)
                msg += f"\n-# {skipped} whitelisted apps remaining"
                await ctx.send(msg, silent=True)

        else:
            apps = await run_in_thread(fetch_authorized_apps, token)
            app_map = {}
            if apps:
                for app in apps:
                    auth_id = app.get("id")
                    name = app.get("application", {}).get("name", "Unknown")
                    app_id = app.get("application", {}).get("id", "?")
                    if auth_id:
                        app_map[auth_id] = {"name": name, "app_id": app_id}

            revoked_lines = []
            failed = []

            for auth_id in targets:
                success = await run_in_thread(revoke_app, token, auth_id)
                if success:
                    info = app_map.get(auth_id, {})
                    name = info.get("name", "Unknown")
                    app_id = info.get("app_id", auth_id)
                    revoked_lines.append(f"* {name} | ||{app_id}||")
                else:
                    failed.append(auth_id)
                await asyncio.sleep(0.3)

            whitelist = get_whitelist()
            if revoked_lines:
                msg = "Successfully unauthorized:\n"
                msg += "\n".join(revoked_lines)
                msg += f"\n-# {len(whitelist)} whitelisted apps remaining"
                await ctx.send(msg, silent=True)
            if failed:
                await ctx.send(f"Failed to revoke: {', '.join(f'`{x}`' for x in failed)}", silent=True)

    @bot.command(name="authwl", description="Add or remove apps from whitelist.")
    async def authwl(ctx, *, args: str = ""):
        await ctx.message.delete()
        parts = args.strip().split()
        if len(parts) < 2:
            await ctx.send("Usage: `<p>authwl add/remove <app_id(s)|all>`", silent=True)
            return

        action = parts[0].lower()
        targets = parts[1:]
        wl = get_whitelist()
        token = get_token()

        if len(targets) == 1 and targets[0].lower() == "all":
            apps = await run_in_thread(fetch_authorized_apps, token)
            if not apps:
                await ctx.send("Failed to fetch apps.", silent=True)
                return
            count = 0
            for app in apps:
                app_id = app.get("application", {}).get("id")
                if action == "add":
                    if app_id and app_id not in wl:
                        wl.append(app_id)
                        count += 1
                elif action == "remove":
                    if app_id in wl:
                        wl = [x for x in wl if x != app_id]
                        count += 1
            save_whitelist(wl)
            await ctx.send(f"{count} app(s) {action}ed {'to' if action == 'add' else 'from'} whitelist.", silent=True)
            return

        apps = await run_in_thread(fetch_authorized_apps, token)
        app_map = {}
        if apps:
            for app in apps:
                aid = app.get("application", {}).get("id")
                name = app.get("application", {}).get("name", "Unknown")
                if aid:
                    app_map[aid] = name

        lines = []
        for app_id in targets:
            if action == "add":
                if app_id not in wl:
                    wl.append(app_id)
                name = app_map.get(app_id, "Unknown")
                lines.append(f"* {name} | ||{app_id}||")
            elif action == "remove":
                wl = [x for x in wl if x != app_id]
                name = app_map.get(app_id, "Unknown")
                lines.append(f"* {name} | ||{app_id}||")

        save_whitelist(wl)

        if action == "add":
            msg = "Successfully whitelisted:\n" + "\n".join(lines)
        else:
            msg = "Successfully removed from whitelist:\n" + "\n".join(lines)

        await ctx.send(msg, silent=True)

AuthScript() 