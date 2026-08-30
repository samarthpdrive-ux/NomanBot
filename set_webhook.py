# ============================================================
# NOMANBOT - TELEGRAM WEBHOOK SETUP
# ============================================================

import asyncio
import os

from aiogram import Bot
from dotenv import load_dotenv


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# CONFIGURATION
# ============================================================

BOT_TOKEN = os.getenv(
    "BOT_TOKEN"
)

WEBHOOK_URL = (
    "https://noman-bot.vercel.app/api/webhook"
)


# ============================================================
# MAIN
# ============================================================

async def main():

    # --------------------------------------------------------
    # TOKEN CHECK
    # --------------------------------------------------------

    if not BOT_TOKEN:

        raise RuntimeError(
            "BOT_TOKEN is not configured."
        )

    # --------------------------------------------------------
    # CREATE BOT
    # --------------------------------------------------------

    bot = Bot(
        token=BOT_TOKEN
    )

    try:

        # ----------------------------------------------------
        # REMOVE OLD WEBHOOK
        # ----------------------------------------------------

        print(
            "Removing previous webhook..."
        )

        await bot.delete_webhook(
            drop_pending_updates=True
        )

        # ----------------------------------------------------
        # SET NEW WEBHOOK
        # ----------------------------------------------------

        print(
            "Setting Vercel webhook..."
        )

        result = await bot.set_webhook(
            url=WEBHOOK_URL,
            drop_pending_updates=True,
        )

        print(
            f"Webhook set result: {result}"
        )

        # ----------------------------------------------------
        # VERIFY WEBHOOK
        # ----------------------------------------------------

        info = await bot.get_webhook_info()

        print()
        print(
            "=============================="
        )
        print(
            "WEBHOOK INFORMATION"
        )
        print(
            "=============================="
        )

        print(
            f"URL: {info.url}"
        )

        print(
            f"Pending updates: "
            f"{info.pending_update_count}"
        )

        print(
            f"Has custom certificate: "
            f"{info.has_custom_certificate}"
        )

        if info.last_error_message:

            print(
                f"Last error: "
                f"{info.last_error_message}"
            )

        else:

            print(
                "Last error: None"
            )

        print(
            "=============================="
        )

    finally:

        await bot.session.close()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    asyncio.run(
        main()
    )
