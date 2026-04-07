import asyncio

@nightyScript(
    name="Server Notification Manager",
    author="Factz",
    description="mutes all useless pings in servers.",
    usage="<p>setnotifs"
)
def ns():
    @bot.command(name="setnotifs", description="set notifs for all servers.")
    async def setnotifs(ctx):
        await ctx.message.delete()

        success = 0
        failed = 0

        for guild in bot.guilds:
            try:
                await bot.http.request(
                    discord.http.Route("PATCH", f"/users/@me/guilds/{guild_id}/settings"),
                    json={
                        "message_notifications": 1,
                        "suppress_everyone": True,
                        "suppress_roles": True,
                        "mute_scheduled_events": True,
                        "mobile_push": True,
                        "notify_highlights": 1,
                        "flags": 0
                    }
                )
                success += 1
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"[notif] failed for {guild_id}: {e}", type_="ERROR")
                failed += 1

        print(f"[notif] {success} succeeded, {failed} failed.", type_="SUCCESS")

ns()
