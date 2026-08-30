from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN

from middleware.membership import BannedUserMiddleware
from handlers.start import router as start_router
from handlers.products import router as products_router
from handlers.orders import router as orders_router
from handlers.deposit import router as deposit_router
from handlers.referral import router as referrals_router
from handlers.support import router as support_router
from handlers.user_promo import router as user_promo_router
from handlers.admin import router as admin_router
from handlers.admin_products import router as admin_products_router
from handlers.admin_product_manage import router as admin_product_manage_router
from handlers.admin_orders import router as admin_orders_router
from handlers.admin_deposits import router as admin_deposits_router
from handlers.admin_support import router as admin_support_router
from handlers.admin_promo import router as admin_promo_router


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI()


# ============================================================
# BOT
# ============================================================

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not configured.")


bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    )
)


# ============================================================
# DISPATCHER
# ============================================================

dp = Dispatcher(
    storage=MemoryStorage()
)


# ============================================================
# MIDDLEWARE
# ============================================================

dp.update.outer_middleware(
    BannedUserMiddleware()
)


# ============================================================
# USER ROUTERS
# ============================================================

dp.include_router(start_router)
dp.include_router(products_router)
dp.include_router(orders_router)
dp.include_router(referrals_router)
dp.include_router(deposit_router)
dp.include_router(user_promo_router)
dp.include_router(support_router)


# ============================================================
# ADMIN ROUTERS
# ============================================================

dp.include_router(admin_router)
dp.include_router(admin_products_router)
dp.include_router(admin_product_manage_router)
dp.include_router(admin_orders_router)
dp.include_router(admin_deposits_router)
dp.include_router(admin_support_router)
dp.include_router(admin_promo_router)


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/")
async def home():
    return {
        "status": "ok",
        "service": "NomanBot",
        "webhook": True
    }


@app.get("/api")
async def api_health():
    return {
        "status": "ok",
        "service": "NomanBot",
        "webhook": True
    }


# ============================================================
# TELEGRAM WEBHOOK
# ============================================================

@app.get("/api/webhook")
async def webhook_health():
    return {
        "status": "ok",
        "service": "NomanBot",
        "webhook": "ready"
    }


@app.post("/api/webhook")
async def telegram_webhook(request: Request):

    try:
        # ----------------------------------------------------
        # Read Telegram update
        # ----------------------------------------------------

        update_data = await request.json()

        # ----------------------------------------------------
        # Convert JSON into aiogram Update
        # ----------------------------------------------------

        from aiogram.types import Update

        update = Update.model_validate(
            update_data,
            context={
                "bot": bot
            }
        )

        # ----------------------------------------------------
        # Process update
        # ----------------------------------------------------

        await dp.feed_update(
            bot,
            update
        )

        # ----------------------------------------------------
        # Telegram expects successful response
        # ----------------------------------------------------

        return JSONResponse(
            status_code=200,
            content={
                "ok": True
            }
        )

    except Exception as exc:

        print(
            f"WEBHOOK ERROR: {type(exc).__name__}: {exc}"
        )

        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "error": str(exc)
            }
        )
