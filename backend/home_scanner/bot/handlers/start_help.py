"""/start and /help — trivial reply handlers."""
from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

WELCOME = (
    "Hey 👋 I watch *xe\\.gr* for new rentals matching your filters and ping you "
    "when something matches\\.\n\n"
    "Use /new to create a saved search\\. /help for everything else\\."
)

HELP = (
    "*Commands*\n"
    "/new — create a saved search \\(location, price, bedrooms\\)\n"
    "/list — list your saved searches\n"
    "/pause `<id>` — pause a saved search\n"
    "/resume `<id>` — resume a paused search\n"
    "/delete `<id>` — delete a saved search\n"
    "/help — this message"
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        await update.effective_message.reply_markdown_v2(WELCOME)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        await update.effective_message.reply_markdown_v2(HELP)
