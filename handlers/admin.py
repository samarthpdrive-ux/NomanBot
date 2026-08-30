# handlers/admin.py — FIXED ADMIN PANEL WITH DASHBOARD, BROADCAST & FULL PROVIDER MANAGEMENT
import asyncio
import json
import logging
from decimal import Decimal, InvalidOperation
from html import escape as html_escape

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest

from sqlalchemy import func, or_

from database import SessionLocal
from config import ADMIN_IDS

from models.user import User
from models.product import Product
from models.order import Order
from models.deposit import Deposit
from models.ticket import Ticket
from models.provider import Provider

from keyboards.admin_menu import get_admin_panel
from keyboards.menu import get_admin_main_menu

from states.broadcast import BroadcastState

logger = logging.getLogger(__name__)
router = Router()


class AdminUserBalanceState(StatesGroup):
    waiting_amount = State()


class ProviderSetupState(StatesGroup):
    waiting_name = State()
    waiting_key = State()
    waiting_base_url = State()
    waiting_api_type = State()
    waiting_auth_type = State()
    waiting_api_key = State()
    waiting_configuration = State()


class ProviderEditState(StatesGroup):
    waiting_field_value = State()


ACTIVITY_PER_PAGE = 8


def _money(value) -> str:
    """Convert Decimal only when rendering Telegram text."""
    return f"${float(value or Decimal('0')):.2f}"


def safe(text: str) -> str:
    return html_escape(str(text), quote=False)


def _validate_base_url(url: str) -> bool:
    """Basic validation for base URLs."""
    u = url.strip().lower()
    return u.startswith("http://") or u.startswith("https://")


async def _safe_edit_text(message: Message, text: str, reply_markup=None, parse_mode: str = "HTML"):
    """Safely edit message text ignoring Telegram 'message is not modified' errors."""
    try:
        return await message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            return None
        raise


# ╔══════════════════════════════════════════════════════════════╗
# ║  ADMIN PANEL KEYBOARD HELPER                                ║
# ╚══════════════════════════════════════════════════════════════╝

def _get_admin_panel_with_providers() -> InlineKeyboardMarkup:
    """Dynamically appends the 🏪 Providers button to the admin panel keyboard."""
    base_markup = get_admin_panel()
    rows = [list(row) for row in base_markup.inline_keyboard]

    provider_btn = InlineKeyboardButton(text="🏪 Providers", callback_data="admin_providers")

    # Prevent duplicate button if already present
    has_provider_btn = any(
        getattr(btn, "callback_data", "") == "admin_providers"
        for row in rows
        for btn in row
    )

    if not has_provider_btn:
        if len(rows) > 1:
            rows.insert(-1, [provider_btn])
        else:
            rows.append([provider_btn])

    return InlineKeyboardMarkup(inline_keyboard=rows)


# ╔══════════════════════════════════════════════════════════════╗
# ║  ADMIN PANEL DASHBOARD — TERMINAL STYLE                    ║
# ╚══════════════════════════════════════════════════════════════╝

def _build_admin_dashboard(db, admin_name: str, admin_id: int) -> str:
    """Build terminal-style admin control center."""
    users = db.query(User).count()
    products = db.query(Product).count()
    orders = db.query(Order).count()
    deposits = db.query(Deposit).count()
    tickets = db.query(Ticket).count()

    admin_user = db.query(User).filter(User.telegram_id == admin_id).first()
    admin_balance = float(getattr(admin_user, 'balance_display', float(admin_user.balance or 0))) if admin_user else 0
    admin_rewards = float(getattr(admin_user, 'referral_earnings_display', 0)) if admin_user else 0
    admin_deposited = float(getattr(admin_user, 'total_deposited', 0) or 0) if admin_user else 0

    total_revenue = db.query(func.coalesce(func.sum(Order.amount), 0)).scalar()

    return (
        "<code>┌──(root㉿ZDeals)-[/control]</code>\n"
        "<code>└─# sudo ZDeals-admin --dashboard</code>\n"
        "<code>[sudo] password:</code>\n"
        "<code>************</code>\n"
        "<code>[AUTH] Administrator Verified</code>\n"
        "<code>[CORE] Control Center Online</code>\n"
        "<code>[SYNC] Commerce Services Ready</code>\n"
        "<code>[MONITOR] Live System Active</code>\n"
        "<code>━━━━━━━━━━━━━━━━━━━━━━</code>\n"
        "<code>CONTROL CENTER</code>\n"
        f"<code>Admin       {admin_name}</code>\n"
        f"<code>UID         {admin_id}</code>\n"
        "<code>Privilege   Root</code>\n"
        "<code>━━━━━━━━━━━━━━━━━━━━━━</code>\n"
        "<code>LEDGER</code>\n"
        f"<code>Balance     ${admin_balance:.2f}</code>\n"
        f"<code>Rewards     ${admin_rewards:.2f}</code>\n"
        f"<code>Deposited   ${admin_deposited:.2f}</code>\n"
        f"<code>Revenue     ${float(total_revenue or 0):.2f}</code>\n"
        "<code>━━━━━━━━━━━━━━━━━━━━━━</code>\n"
        "<code>SYSTEM</code>\n"
        f"<code>Orders      {orders}</code>\n"
        "<code>Status      Operational</code>\n"
        "<code>━━━━━━━━━━━━━━━━━━━━━━</code>\n"
        "<code>Awaiting administrator command...</code>\n"
        "<code>root@ZDeals:~#</code>\n\n"
        "👇 <b>Choose an action:</b>"
    )


# ╔══════════════════════════════════════════════════════════════╗
# ║  USER DASHBOARD — TERMINAL STYLE (for admin_back)          ║
# ╚══════════════════════════════════════════════════════════════╝

def _build_user_dashboard(user) -> str:
    """Build terminal-style user dashboard."""
    balance = float(getattr(user, 'balance_display', float(user.balance or 0)))
    total_orders = int(getattr(user, 'total_orders', 0) or 0)
    total_refs = int(getattr(user, 'total_referrals', 0) or 0)
    first_name = user.full_name.split()[0] if user.full_name else "user"

    return (
        "🛍 ZDeals Store\n"
        "Premium Digital Marketplace\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👋 Welcome back, {safe(first_name)}\n\n"
        "💎 Standard Plan\n\n"
        f"💰 Wallet: ${balance:.2f}\n"
        f"📦 Orders: {total_orders}\n"
        f"🎁 Rewards: {total_refs}\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"

        "<blockquote>"
        "✓ Verified Premium Products\n"
        "✓ Instant Delivery\n"
        "✓ Secure Payments\n"
        "✓ Dedicated Customer Support"
        "</blockquote>\n\n"

        "━━━━━━━━━━━━━━━━━━━━\n\n"

        "<blockquote>"
        "🛒 Shop \"Browse premium digital products\"\n"
        "💰 Deposit \"Top up your wallet instantly\"\n"
        "👤 Profile \"Manage your account & wallet\"\n"
        "📦 Orders \"View purchases & product keys\"\n"
        "📞 Support \"Get help from our support team\""
        "</blockquote>\n\n"

        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "📢 Stay Updated: @Senacoun\n\n"
        "👇 Tap a button below to get started."
    )


# =====================================================
# /admin COMMAND
# =====================================================

@router.message(Command("admin"))
async def admin_cmd(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    await message.answer(
        "👑 Tap the crown button on your dashboard above to open the Admin Panel.\n\n"
        "(Send /start if you don't see your dashboard.)"
    )


# =====================================================
# ADMIN PANEL
# =====================================================

@router.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Access denied.", show_alert=True)
        return

    await state.clear()
    db = SessionLocal()
    try:
        text = _build_admin_dashboard(db, callback.from_user.full_name, callback.from_user.id)

        await _safe_edit_text(
            callback.message,
            text,
            reply_markup=_get_admin_panel_with_providers(),
            parse_mode="HTML"
        )
    finally:
        db.close()

    await callback.answer()


# ============================================================
# PROVIDER MANAGEMENT
# ============================================================

@router.callback_query(F.data.in_({"admin_providers", "admin:providers"}))
async def admin_providers(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Access denied.", show_alert=True)
        return

    await state.clear()

    text = (
        "🏪 <b>PROVIDER MANAGEMENT</b>\n\n"
        "<code>┌──(root㉿ZDeals)-[/providers]</code>\n"
        "<code>└─# sudo stockctl provider --status</code>\n"
        "<code>[SYS] Provider Subsystem Ready</code>\n\n"
        "Manage API providers, credentials, and supplier connections.\n\n"
        "👇 Select an action below:"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 Providers", callback_data="admin_provider_list")],
            [InlineKeyboardButton(text="➕ Add Provider", callback_data="admin_provider_add")],
            [InlineKeyboardButton(text="🔄 Refresh", callback_data="admin_providers")],
            [InlineKeyboardButton(text="🔙 Back", callback_data="admin_panel")]
        ]
    )

    await _safe_edit_text(callback.message, text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.in_({"admin_provider_list", "admin:providers:list"}))
async def admin_provider_list(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Access denied.", show_alert=True)
        return

    await state.clear()
    db = SessionLocal()
    try:
        providers = db.query(Provider).order_by(Provider.id.asc()).all()

        if not providers:
            text = (
                "🏪 <b>PROVIDER LIST</b>\n\n"
                "⚠️ <i>No providers configured in database.</i>\n\n"
                "Click ➕ <b>Add Provider</b> to configure your first provider."
            )
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="➕ Add Provider", callback_data="admin_provider_add")],
                    [InlineKeyboardButton(text="🔙 Back", callback_data="admin_providers")]
                ]
            )
            await _safe_edit_text(callback.message, text, reply_markup=keyboard, parse_mode="HTML")
            await callback.answer()
            return

        lines = ["🏪 <b>CONFIGURED PROVIDERS</b>\n"]
        buttons = []

        for p in providers:
            status_str = "🟢 Active" if p.is_active else "🔴 Inactive"
            lines.append(
                f"• <b>{safe(p.name)}</b> (<code>{safe(p.provider_key)}</code>)\n"
                f"  URL: <code>{safe(p.base_url)}</code>\n"
                f"  Type: <code>{safe(p.api_type)}</code> | Auth: <code>{safe(p.auth_type)}</code>\n"
                f"  Status: {status_str}\n"
            )

            buttons.append([
                InlineKeyboardButton(text=f"✏️ Edit {p.name[:12]}", callback_data=f"admin_provider_edit_{p.id}"),
                InlineKeyboardButton(
                    text="🔴 Disable" if p.is_active else "🟢 Enable",
                    callback_data=f"admin_provider_toggle_{p.id}"
                ),
                InlineKeyboardButton(text="🗑 Delete", callback_data=f"admin_provider_delete_{p.id}")
            ])

        buttons.append([InlineKeyboardButton(text="➕ Add Provider", callback_data="admin_provider_add")])
        buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="admin_providers")])

        await _safe_edit_text(
            callback.message,
            "\n".join(lines),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
            parse_mode="HTML"
        )
    finally:
        db.close()

    await callback.answer()


@router.callback_query(F.data.in_({"admin_provider_add", "admin:providers:add"}))
async def admin_provider_add(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Access denied.", show_alert=True)
        return

    await state.clear()
    text = (
        "🏪 <b>ADD PROVIDER</b>\n\n"
        "How do you want to configure this provider?"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🤖 Automatic Setup", callback_data="admin_provider_auto")],
            [InlineKeyboardButton(text="🛠 Manual Setup", callback_data="admin_provider_manual")],
            [InlineKeyboardButton(text="❌ Cancel", callback_data="admin_provider_list")]
        ]
    )

    await _safe_edit_text(callback.message, text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.in_({"admin_provider_auto", "admin:provider:auto"}))
async def admin_provider_auto(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Access denied.", show_alert=True)
        return

    text = (
        "🤖 <b>AUTOMATIC API SETUP</b>\n\n"
        "🤖 Automatic API setup is not available yet.\n\n"
        "Please use 🛠 <b>Manual Setup</b> to add your provider details."
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛠 Manual Setup", callback_data="admin_provider_manual")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="admin_provider_add")]
        ]
    )

    await _safe_edit_text(callback.message, text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


# ============================================================
# MANUAL SETUP FSM FLOW
# ============================================================

@router.callback_query(F.data.in_({"admin_provider_manual", "admin:provider:manual"}))
async def start_provider_manual_setup(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Access denied.", show_alert=True)
        return

    await state.clear()
    await state.set_state(ProviderSetupState.waiting_name)

    text = (
        "🛠 <b>MANUAL PROVIDER SETUP (Step 1/7)</b>\n\n"
        "Please send the <b>Provider Name</b>.\n\n"
        "<i>Example: Noman Shop Bot or Supplier X</i>"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data="admin_provider_cancel")]
        ]
    )

    await _safe_edit_text(callback.message, text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.message(ProviderSetupState.waiting_name)
async def process_provider_name(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await state.clear()
        return

    name = (message.text or "").strip()
    if not name or len(name) < 2:
        await message.answer("❌ <b>Invalid Name!</b> Please send a valid provider name (at least 2 characters).", parse_mode="HTML")
        return

    await state.update_data(name=name)
    await state.set_state(ProviderSetupState.waiting_key)

    default_key = name.lower().replace(" ", "_").replace("-", "_")
    default_key = "".join(c for c in default_key if c.isalnum() or c == "_")

    await message.answer(
        f"✅ <b>Name:</b> {safe(name)}\n\n"
        "🛠 <b>MANUAL PROVIDER SETUP (Step 2/7)</b>\n\n"
        "Please send a unique <b>Provider Key</b> (slug identifier).\n\n"
        f"<i>Suggested: <code>{safe(default_key)}</code></i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data="admin_provider_cancel")]]
        )
    )


@router.message(ProviderSetupState.waiting_key)
async def process_provider_key(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await state.clear()
        return

    raw_key = (message.text or "").strip().lower()
    clean_key = "".join(c for c in raw_key if c.isalnum() or c in ("_", "-"))

    if not clean_key:
        await message.answer("❌ <b>Invalid Key!</b> Key must contain letters, numbers, hyphens, or underscores.", parse_mode="HTML")
        return

    db = SessionLocal()
    try:
        existing = db.query(Provider).filter(Provider.provider_key == clean_key).first()
        if existing:
            await message.answer("❌ <b>Provider key already exists!</b> Please send a different unique provider key.", parse_mode="HTML")
            return
    finally:
        db.close()

    await state.update_data(provider_key=clean_key)
    await state.set_state(ProviderSetupState.waiting_base_url)

    await message.answer(
        f"✅ <b>Provider Key:</b> <code>{safe(clean_key)}</code>\n\n"
        "🛠 <b>MANUAL PROVIDER SETUP (Step 3/7)</b>\n\n"
        "Please send the <b>Base URL</b> of the provider API.\n\n"
        "<i>Example: https://api.supplier.com</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data="admin_provider_cancel")]]
        )
    )


@router.message(ProviderSetupState.waiting_base_url)
async def process_provider_base_url(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await state.clear()
        return

    url = (message.text or "").strip().rstrip("/")
    if not _validate_base_url(url):
        await message.answer("❌ <b>Invalid URL!</b> Base URL must start with <code>http://</code> or <code>https://</code>.", parse_mode="HTML")
        return

    await state.update_data(base_url=url)
    await state.set_state(ProviderSetupState.waiting_api_type)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="excalibur", callback_data="set_apitype_excalibur"),
                InlineKeyboardButton(text="generic", callback_data="set_apitype_generic"),
                InlineKeyboardButton(text="rest", callback_data="set_apitype_rest")
            ],
            [InlineKeyboardButton(text="❌ Cancel", callback_data="admin_provider_cancel")]
        ]
    )

    await message.answer(
        f"✅ <b>Base URL:</b> <code>{safe(url)}</code>\n\n"
        "🛠 <b>MANUAL PROVIDER SETUP (Step 4/7)</b>\n\n"
        "Select or send the <b>API Type</b>:\n"
        "• <code>excalibur</code> (Excalibur reseller API format)\n"
        "• <code>generic</code> (Standard REST API format)\n"
        "• <code>rest</code> (Custom REST format)",
        parse_mode="HTML",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("set_apitype_"))
async def process_provider_api_type_cb(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Access denied.", show_alert=True)
        return

    api_type = callback.data.removeprefix("set_apitype_")
    await state.update_data(api_type=api_type)
    await state.set_state(ProviderSetupState.waiting_auth_type)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="header (X-API-Key)", callback_data="set_authtype_header"),
                InlineKeyboardButton(text="bearer (Bearer Token)", callback_data="set_authtype_bearer")
            ],
            [
                InlineKeyboardButton(text="query (URL Param)", callback_data="set_authtype_query"),
                InlineKeyboardButton(text="api_key", callback_data="set_authtype_api_key")
            ],
            [InlineKeyboardButton(text="❌ Cancel", callback_data="admin_provider_cancel")]
        ]
    )

    await _safe_edit_text(
        callback.message,
        f"✅ <b>API Type:</b> <code>{safe(api_type)}</code>\n\n"
        "🛠 <b>MANUAL PROVIDER SETUP (Step 5/7)</b>\n\n"
        "Select or send the <b>Authentication Type</b>:",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()


@router.message(ProviderSetupState.waiting_api_type)
async def process_provider_api_type_msg(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await state.clear()
        return

    api_type = (message.text or "").strip().lower() or "generic"
    await state.update_data(api_type=api_type)
    await state.set_state(ProviderSetupState.waiting_auth_type)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="header (X-API-Key)", callback_data="set_authtype_header"),
                InlineKeyboardButton(text="bearer (Bearer Token)", callback_data="set_authtype_bearer")
            ],
            [
                InlineKeyboardButton(text="query (URL Param)", callback_data="set_authtype_query"),
                InlineKeyboardButton(text="api_key", callback_data="set_authtype_api_key")
            ],
            [InlineKeyboardButton(text="❌ Cancel", callback_data="admin_provider_cancel")]
        ]
    )

    await message.answer(
        f"✅ <b>API Type:</b> <code>{safe(api_type)}</code>\n\n"
        "🛠 <b>MANUAL PROVIDER SETUP (Step 5/7)</b>\n\n"
        "Select or send the <b>Authentication Type</b>:",
        parse_mode="HTML",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("set_authtype_"))
async def process_provider_auth_type_cb(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Access denied.", show_alert=True)
        return

    auth_type = callback.data.removeprefix("set_authtype_")
    await state.update_data(auth_type=auth_type)
    await state.set_state(ProviderSetupState.waiting_api_key)

    await _safe_edit_text(
        callback.message,
        f"✅ <b>Auth Type:</b> <code>{safe(auth_type)}</code>\n\n"
        "🛠 <b>MANUAL PROVIDER SETUP (Step 6/7)</b>\n\n"
        "Please send the <b>API Key / Token</b> for this provider.\n\n"
        "<i>Send 'none' or 'skip' if no key is required.</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data="admin_provider_cancel")]]
        )
    )
    await callback.answer()


@router.message(ProviderSetupState.waiting_auth_type)
async def process_provider_auth_type_msg(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await state.clear()
        return

    auth_type = (message.text or "").strip().lower() or "api_key"
    await state.update_data(auth_type=auth_type)
    await state.set_state(ProviderSetupState.waiting_api_key)

    await message.answer(
        f"✅ <b>Auth Type:</b> <code>{safe(auth_type)}</code>\n\n"
        "🛠 <b>MANUAL PROVIDER SETUP (Step 6/7)</b>\n\n"
        "Please send the <b>API Key / Token</b> for this provider.\n\n"
        "<i>Send 'none' or 'skip' if no key is required.</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data="admin_provider_cancel")]]
        )
    )


@router.message(ProviderSetupState.waiting_api_key)
async def process_provider_api_key(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await state.clear()
        return

    raw_key = (message.text or "").strip()
    api_key = None if raw_key.lower() in ("none", "skip", "") else raw_key

    await state.update_data(api_key=api_key)
    await state.set_state(ProviderSetupState.waiting_configuration)

    await message.answer(
        "✅ <b>API Key saved securely (hidden)</b>\n\n"
        "🛠 <b>MANUAL PROVIDER SETUP (Step 7/7)</b>\n\n"
        "Send additional JSON configuration (optional) or send <b>skip</b>:\n\n"
        "<i>Example:</i> <code>{\"products_endpoint\": \"/api/v1/products\"}</code>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⏩ Skip Configuration", callback_data="skip_provider_config")]]
        )
    )


@router.callback_query(F.data == "skip_provider_config")
async def skip_provider_config(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Access denied.", show_alert=True)
        return

    await state.update_data(configuration=None)
    await show_provider_preview(callback, state)


@router.message(ProviderSetupState.waiting_configuration)
async def process_provider_configuration(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await state.clear()
        return

    raw_text = (message.text or "").strip()
    if raw_text.lower() in ("skip", "none", ""):
        config_val = None
    else:
        try:
            json.loads(raw_text)
            config_val = raw_text
        except Exception:
            await message.answer("❌ <b>Invalid JSON format!</b> Please send valid JSON or send 'skip'.", parse_mode="HTML")
            return

    await state.update_data(configuration=config_val)
    await show_provider_preview(message, state)


async def show_provider_preview(target: Message | CallbackQuery, state: FSMContext):
    data = await state.get_data()

    preview_text = (
        "🏪 <b>PROVIDER PREVIEW</b>\n\n"
        f"<b>Name:</b> {safe(data.get('name', ''))}\n"
        f"<b>Key:</b> <code>{safe(data.get('provider_key', ''))}</code>\n"
        f"<b>Base URL:</b> <code>{safe(data.get('base_url', ''))}</code>\n"
        f"<b>API Type:</b> <code>{safe(data.get('api_type', 'generic'))}</code>\n"
        f"<b>Auth Type:</b> <code>{safe(data.get('auth_type', 'api_key'))}</code>\n"
        f"<b>API Key:</b> ********\n"
        f"<b>Configuration:</b> <code>{safe(data.get('configuration') or 'None')}</code>\n\n"
        "Save this provider?"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Save", callback_data="admin_provider_save_confirm"),
                InlineKeyboardButton(text="❌ Cancel", callback_data="admin_provider_cancel")
            ]
        ]
    )

    if isinstance(target, CallbackQuery):
        await _safe_edit_text(target.message, preview_text, reply_markup=keyboard, parse_mode="HTML")
        await target.answer()
    else:
        await target.answer(preview_text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "admin_provider_save_confirm")
async def save_provider_to_db(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Access denied.", show_alert=True)
        return

    data = await state.get_data()
    db = SessionLocal()
    try:
        provider = Provider(
            name=data["name"],
            provider_key=data["provider_key"],
            base_url=data["base_url"],
            api_type=data.get("api_type", "generic"),
            auth_type=data.get("auth_type", "api_key"),
            api_key=data.get("api_key"),
            configuration=data.get("configuration"),
            is_active=True,
        )
        db.add(provider)
        db.commit()
        db.refresh(provider)
        prov_name = provider.name
    except Exception as e:
        db.rollback()
        logger.exception("Failed to save provider to database")
        await _safe_edit_text(
            callback.message,
            f"❌ <b>Database Error:</b> Could not save provider.\n<code>{safe(str(e))}</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Provider List", callback_data="admin_provider_list")]])
        )
        await state.clear()
        return
    finally:
        db.close()

    await state.clear()
    await _safe_edit_text(
        callback.message,
        f"✅ <b>Provider Saved Successfully!</b>\n\nProvider <b>{safe(prov_name)}</b> is now ready for use.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="📋 Provider List", callback_data="admin_provider_list")]]
        )
    )
    await callback.answer()


@router.callback_query(F.data == "admin_provider_cancel")
async def cancel_provider_setup(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Access denied.", show_alert=True)
        return

    await state.clear()
    await callback.answer("❌ Provider setup cancelled.")
    await admin_provider_list(callback, state)


# ============================================================
# TOGGLE / DELETE / EDIT PROVIDERS
# ============================================================

@router.callback_query(F.data.startswith("admin_provider_toggle_"))
async def toggle_provider(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Access denied.", show_alert=True)
        return

    provider_id = int(callback.data.removeprefix("admin_provider_toggle_"))
    db = SessionLocal()
    try:
        p = db.query(Provider).filter(Provider.id == provider_id).first()
        if not p:
            await callback.answer("Provider not found.", show_alert=True)
            return

        p.is_active = not p.is_active
        db.commit()
        status_msg = f"🟢 {p.name} Enabled" if p.is_active else f"🔴 {p.name} Disabled"
    finally:
        db.close()

    await callback.answer(status_msg, show_alert=True)
    await admin_provider_list(callback, state)


@router.callback_query(F.data.startswith("admin_provider_delete_"))
async def delete_provider_confirm(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Access denied.", show_alert=True)
        return

    provider_id = int(callback.data.removeprefix("admin_provider_delete_"))
    db = SessionLocal()
    try:
        p = db.query(Provider).filter(Provider.id == provider_id).first()
        if not p:
            await callback.answer("Provider not found.", show_alert=True)
            return

        text = (
            "⚠️ <b>Delete Provider?</b>\n\n"
            f"Provider: <b>{safe(p.name)}</b> (<code>{safe(p.provider_key)}</code>)\n\n"
            "This action cannot be undone."
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Confirm Delete", callback_data=f"admin_provider_confirmdel_{p.id}"),
                    InlineKeyboardButton(text="❌ Cancel", callback_data="admin_provider_list")
                ]
            ]
        )

        await _safe_edit_text(callback.message, text, reply_markup=keyboard, parse_mode="HTML")
    finally:
        db.close()

    await callback.answer()


@router.callback_query(F.data.startswith("admin_provider_confirmdel_"))
async def delete_provider_execute(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Access denied.", show_alert=True)
        return

    provider_id = int(callback.data.removeprefix("admin_provider_confirmdel_"))
    db = SessionLocal()
    try:
        p = db.query(Provider).filter(Provider.id == provider_id).first()
        if not p:
            await callback.answer("Provider not found.", show_alert=True)
            return

        conds = []
        if hasattr(Product, "provider_id"):
            conds.append(Product.provider_id == p.id)
        if hasattr(Product, "reseller_name"):
            conds.append(Product.reseller_name == p.name)
        if hasattr(Product, "reseller_id"):
            conds.append(Product.reseller_id == str(p.id))
            conds.append(Product.reseller_id == p.provider_key)

        products_using = db.query(Product).filter(or_(*conds)).first() if conds else None

        if products_using:
            await _safe_edit_text(
                callback.message,
                f"❌ <b>Cannot Delete Provider</b>\n\n"
                f"This provider (<b>{safe(p.name)}</b>) is still used by active products in store.\n\n"
                f"Please remove or reassign those products first.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📋 Provider List", callback_data="admin_provider_list")]])
            )
            await callback.answer()
            return

        db.delete(p)
        db.commit()
        await callback.answer("✅ Provider deleted successfully.", show_alert=True)
    finally:
        db.close()

    await admin_provider_list(callback, state)


@router.callback_query(F.data.startswith("admin_provider_edit_"))
async def edit_provider_menu(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Access denied.", show_alert=True)
        return

    provider_id = int(callback.data.removeprefix("admin_provider_edit_"))
    db = SessionLocal()
    try:
        p = db.query(Provider).filter(Provider.id == provider_id).first()
        if not p:
            await callback.answer("Provider not found.", show_alert=True)
            return

        text = (
            f"✏️ <b>EDIT PROVIDER: {safe(p.name)}</b>\n\n"
            f"<b>Key:</b> <code>{safe(p.provider_key)}</code>\n"
            f"<b>Base URL:</b> <code>{safe(p.base_url)}</code>\n"
            f"<b>API Type:</b> <code>{safe(p.api_type)}</code>\n"
            f"<b>Auth Type:</b> <code>{safe(p.auth_type)}</code>\n"
            f"<b>API Key:</b> ********\n\n"
            "Select a field to edit:"
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="Name", callback_data=f"pedit_field_name_{p.id}"),
                    InlineKeyboardButton(text="Base URL", callback_data=f"pedit_field_base_url_{p.id}")
                ],
                [
                    InlineKeyboardButton(text="API Type", callback_data=f"pedit_field_api_type_{p.id}"),
                    InlineKeyboardButton(text="Auth Type", callback_data=f"pedit_field_auth_type_{p.id}")
                ],
                [
                    InlineKeyboardButton(text="API Key / Token", callback_data=f"pedit_field_api_key_{p.id}"),
                    InlineKeyboardButton(text="Configuration", callback_data=f"pedit_field_configuration_{p.id}")
                ],
                [InlineKeyboardButton(text="⬅️ Back", callback_data="admin_provider_list")]
            ]
        )

        await _safe_edit_text(callback.message, text, reply_markup=keyboard, parse_mode="HTML")
    finally:
        db.close()

    await callback.answer()


@router.callback_query(F.data.startswith("pedit_field_"))
async def prompt_edit_provider_field(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Access denied.", show_alert=True)
        return

    parts = callback.data.split("_")
    field_name = "_".join(parts[2:-1])
    provider_id = int(parts[-1])

    await state.update_data(edit_provider_id=provider_id, edit_field=field_name)
    await state.set_state(ProviderEditState.waiting_field_value)

    prompt = f"Send the new value for <b>{field_name}</b>:"
    if field_name == "api_key":
        prompt += "\n\n<i>Current API key is hidden. Send a new key to update or 'keep' to keep existing.</i>"

    await _safe_edit_text(
        callback.message,
        prompt,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data=f"admin_provider_edit_{provider_id}")]])
    )
    await callback.answer()


@router.message(ProviderEditState.waiting_field_value)
async def process_edit_provider_field_save(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await state.clear()
        return

    data = await state.get_data()
    provider_id = data.get("edit_provider_id")
    field_name = data.get("edit_field")
    new_val = (message.text or "").strip()

    if field_name == "api_key" and new_val.lower() == "keep":
        await state.clear()
        await message.answer("Existing API key kept.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📋 Provider List", callback_data="admin_provider_list")]]))
        return

    db = SessionLocal()
    try:
        p = db.query(Provider).filter(Provider.id == provider_id).first()
        if not p:
            await message.answer("Provider not found.")
            await state.clear()
            return

        if field_name == "base_url" and not _validate_base_url(new_val):
            await message.answer("❌ Invalid URL! Base URL must start with <code>http://</code> or <code>https://</code>.", parse_mode="HTML")
            return

        if field_name == "configuration" and new_val.lower() not in ("none", "skip", "null"):
            try:
                json.loads(new_val)
            except Exception:
                await message.answer("❌ Invalid JSON format for configuration.", parse_mode="HTML")
                return

        setattr(p, field_name, new_val)
        db.commit()
        await message.answer(
            f"✅ Provider <b>{field_name}</b> updated!",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📋 Provider List", callback_data="admin_provider_list")]])
        )
    finally:
        db.close()
        await state.clear()


# =====================================================
# USERS
# =====================================================

@router.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Access denied.", show_alert=True)
        return

    db = SessionLocal()
    try:
        users = db.query(User).order_by(User.id.desc()).limit(50).all()
        keyboard = [
            [
                InlineKeyboardButton(
                    text=f"👤 {u.full_name} | {u.telegram_id}",
                    callback_data=f"view_user_{u.id}"
                )
            ]
            for u in users
        ]
        keyboard.append([
            InlineKeyboardButton(text="⬅ Back", callback_data="admin_panel")
        ])

        await _safe_edit_text(
            callback.message,
            f"👥 <b>Users ({len(users)})</b>\n\n<i>Showing latest 50</i>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode="HTML"
        )
    finally:
        db.close()
    await callback.answer()


@router.callback_query(F.data.startswith("view_user_"))
async def view_user(callback: CallbackQuery):
    uid = int(callback.data.split("_")[2])
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == uid).first()
        if not user:
            await callback.answer("User not found.", show_alert=True)
            return

        text = (
            "╔════════════════════════════╗\n"
            "║      👤 USER DETAILS       ║\n"
            "╚════════════════════════════╝\n\n"
            f"👤 <b>Name:</b> {safe(user.full_name)}\n"
            f"📝 <b>Username:</b> @{safe(user.username or 'None')}\n"
            f"🆔 <b>Telegram ID:</b> <code>{safe(str(user.telegram_id))}</code>\n\n"
            "────────────────────────────\n"
            f"💰 <b>Balance:</b> ${float(user.balance):.2f}\n"
            f"🎁 <b>Referral Earnings:</b> ${float(user.referral_earnings):.2f}\n"
            f"👥 <b>Referrals:</b> {user.total_referrals}\n\n"
            "────────────────────────────\n"
            f"🛒 <b>Orders:</b> {user.total_orders}\n"
            f"💸 <b>Total Spent:</b> ${float(user.total_spent):.2f}\n"
            f"📥 <b>Total Deposited:</b> ${float(user.total_deposited):.2f}\n\n"
            "────────────────────────────\n"
            f"🚫 <b>Banned:</b> {'<b>YES</b> 🚫' if user.is_banned else 'No 🟢'}"
        )

        await _safe_edit_text(
            callback.message,
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="➕ Add / Remove Balance",
                            callback_data=f"user_balance_adjust_{user.id}"
                        ),
                        InlineKeyboardButton(
                            text="✏️ Set Balance",
                            callback_data=f"user_balance_set_{user.id}"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="🛒 Purchase History",
                            callback_data=f"user_orders_{user.id}_0"
                        ),
                        InlineKeyboardButton(
                            text="📥 Deposit History",
                            callback_data=f"user_deposits_{user.id}_0"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="📦 Product Summary",
                            callback_data=f"user_products_{user.id}"
                        ),
                        InlineKeyboardButton(
                            text="✅ Unban" if user.is_banned else "🚫 Ban",
                            callback_data=f"user_ban_{user.id}"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="🔙 Back to Users",
                            callback_data="admin_users"
                        )
                    ]
                ]
            )
        )
    finally:
        db.close()
    await callback.answer()


# =====================================================
# PRODUCTS
# =====================================================

@router.callback_query(F.data == "admin_products")
async def admin_products(callback: CallbackQuery):
    db = SessionLocal()
    try:
        products = db.query(Product).order_by(Product.id.desc()).all()

        keyboard = [
            [
                InlineKeyboardButton(
                    text="➕ New Product",
                    callback_data="create_product"
                )
            ]
        ]

        for product in products:
            status = "🟢" if product.is_active else "🔴"
            keyboard.append([
                InlineKeyboardButton(
                    text=f"#{product.id} {status} {product.icon} {product.name} ({product.stock})",
                    callback_data=f"manage_{product.id}"
                )
            ])

        keyboard.append([
            InlineKeyboardButton(text="⬅ Back", callback_data="admin_panel")
        ])

        await _safe_edit_text(
            callback.message,
            "📦 <b>Product Management</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
    finally:
        db.close()
    await callback.answer()


# =====================================================
# STATISTICS
# =====================================================

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    db = SessionLocal()
    try:
        users = db.query(User).count()
        products = db.query(Product).count()
        orders = db.query(Order).count()
        deposits = db.query(Deposit).count()
        tickets = db.query(Ticket).count()
        revenue = db.query(func.coalesce(func.sum(Order.amount), 0)).scalar()

        text = (
            "╔════════════════════════════╗\n"
            "║      📊 STATISTICS         ║\n"
            "╚════════════════════════════╝\n\n"
            f"👥 <b>Users:</b> {users}\n"
            f"📦 <b>Products:</b> {products}\n"
            f"🛒 <b>Orders:</b> {orders}\n"
            f"💰 <b>Deposits:</b> {deposits}\n"
            f"🎫 <b>Tickets:</b> {tickets}\n\n"
            "════════════════════════════\n"
            f"💵 <b>Revenue:</b> ${float(revenue or 0):.2f}"
        )

        await _safe_edit_text(
            callback.message,
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="⬅ Back", callback_data="admin_panel")]
                ]
            )
        )
    finally:
        db.close()
    await callback.answer()


# =====================================================
# BROADCAST — FULLY FIXED
# =====================================================

@router.callback_query(F.data == "admin_broadcast")
async def broadcast_start(callback: CallbackQuery, state: FSMContext):
    """Start broadcast mode — sets FSM state and waits for message."""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Access denied.", show_alert=True)
        return

    # Set state to wait for broadcast message
    await state.set_state(BroadcastState.waiting_message)

    await _safe_edit_text(
        callback.message,
        "📢 <b>Broadcast Mode Activated</b>\n\n"
        "✏️ Send me the message you want to broadcast to <b>ALL users</b>.\n\n"
        "📝 <i>You can send text, photos, videos, documents — anything!</i>\n\n"
        "⚠️ <i>This will be forwarded to every user in the database.</i>\n\n"
        "👇 Click Cancel to abort.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Cancel Broadcast", callback_data="cancel_broadcast")]
            ]
        )
    )

    await callback.answer("📢 Broadcast mode activated — send your message now.")


@router.callback_query(F.data == "cancel_broadcast")
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    """Cancel the broadcast and return to admin panel."""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Access denied.", show_alert=True)
        return

    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()

    db = SessionLocal()
    try:
        text = _build_admin_dashboard(db, callback.from_user.full_name, callback.from_user.id)
        await _safe_edit_text(
            callback.message,
            text,
            reply_markup=_get_admin_panel_with_providers(),
            parse_mode="HTML"
        )
    finally:
        db.close()

    await callback.answer("❌ Broadcast cancelled.")


@router.message(BroadcastState.waiting_message)
async def send_broadcast(message: Message, state: FSMContext):
    """Handle the broadcast message and send to all users."""
    if message.from_user.id not in ADMIN_IDS:
        await state.clear()
        await message.answer("⛔ Access denied. You are not an admin.")
        return

    # Send initial status message
    status_msg = await message.answer(
        "📢 <b>Broadcasting...</b>\n\n⏳ Fetching users from database...",
        parse_mode="HTML"
    )

    db = SessionLocal()
    try:
        users = db.query(User.telegram_id).all()
        user_ids = [x[0] for x in users]
    finally:
        db.close()

    if not user_ids:
        await status_msg.edit_text("⚠️ <b>No users found in database!</b>", parse_mode="HTML")
        await state.clear()
        return

    total = len(user_ids)
    sent = 0
    failed = 0
    blocked = 0
    deactivated = 0
    not_started = 0
    unknown_error = 0
    error_details = []

    # Update status message
    await status_msg.edit_text(
        f"📢 <b>Broadcasting...</b>\n\n"
        f"📊 Total users: {total}\n"
        f"✅ Sent: 0\n"
        f"❌ Failed: 0\n\n"
        f"⏳ Starting broadcast...",
        parse_mode="HTML"
    )

    # Send to each user with detailed error tracking
    for i, user_id in enumerate(user_ids, 1):
        try:
            await message.copy_to(chat_id=user_id)
            sent += 1

            # Small delay to avoid hitting rate limits
            if i % 5 == 0:
                await asyncio.sleep(0.1)

        except Exception as e:
            error_str = str(e).lower()

            if "bot was blocked by the user" in error_str or "blocked" in error_str:
                blocked += 1
            elif "user is deactivated" in error_str or "deactivated" in error_str:
                deactivated += 1
            elif "chat not found" in error_str:
                not_started += 1
            elif "bot can't initiate conversation" in error_str:
                not_started += 1
            else:
                failed += 1
                unknown_error += 1
                if len(error_details) < 5:
                    error_details.append(f"UID {user_id}: {str(e)[:100]}")

        # Update progress every 5 users or on last user
        if i % 5 == 0 or i == total:
            try:
                progress_text = (
                    f"📢 <b>Broadcasting...</b>\n\n"
                    f"📊 Progress: {i}/{total}\n"
                    f"✅ Sent: {sent}\n"
                    f"❌ Failed: {failed}\n"
                    f"🚫 Blocked: {blocked}\n\n"
                    f"⏳ Still sending..."
                )
                await status_msg.edit_text(progress_text, parse_mode="HTML")
            except Exception:
                pass

    # Calculate stats
    total_failed = blocked + deactivated + not_started + unknown_error
    success_rate = (sent / total * 100) if total > 0 else 0

    # Build detailed result message
    result_text = (
        f"📢 <b>✅ Broadcast Complete!</b>\n\n"
        f"<code>═══════════════════════</code>\n"
        f"📊 <b>Total Users in DB:</b> {total}\n"
        f"<code>═══════════════════════</code>\n"
        f"✅ <b>Successfully Sent:</b> {sent}\n"
        f"📈 <b>Success Rate:</b> {success_rate:.1f}%\n"
        f"<code>═══════════════════════</code>\n"
        f"❌ <b>Failed to Deliver:</b> {total_failed}\n"
        f"  ├ 🚫 <b>Blocked Bot:</b> {blocked}\n"
        f"  ├ 💀 <b>Deactivated Account:</b> {deactivated}\n"
        f"  ├ 🔇 <b>Never Started Bot:</b> {not_started}\n"
        f"  └ ⚠️ <b>Unknown Error:</b> {unknown_error}\n"
        f"<code>═══════════════════════</code>\n\n"
    )

    if blocked > 0 or deactivated > 0 or not_started > 0:
        result_text += "<b>ℹ️ Why so many failed?</b>\n"
        if not_started > 0:
            result_text += "• <b>Never started:</b> Users who haven't sent /start to the bot cannot receive messages (Telegram API restriction)\n"
        if blocked > 0:
            result_text += "• <b>Blocked:</b> Users who blocked the bot\n"
        if deactivated > 0:
            result_text += "• <b>Deactivated:</b> Users who deleted their Telegram account\n"
        result_text += "\n"

    if error_details:
        result_text += (
            f"<b>⚠️ Unknown Errors (first {len(error_details)}):</b>\n"
            f"<code>{chr(10).join(error_details)}</code>\n\n"
        )

    result_text += "<i>💡 Only users who have started the bot and not blocked it can receive broadcasts.</i>"

    await status_msg.edit_text(
        result_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="🔄 Broadcast Again", callback_data="admin_broadcast"),
                    InlineKeyboardButton(text="🔙 Admin Panel", callback_data="admin_panel")
                ]
            ]
        )
    )

    await state.clear()


# =====================================================
# BACK TO USER PANEL — Terminal style, NO popup
# =====================================================

@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    """Back to user dashboard — terminal style, edits current message."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()

        if not user:
            await callback.answer("User not found.", show_alert=True)
            return

        text = _build_user_dashboard(user)

        await _safe_edit_text(
            callback.message,
            text,
            reply_markup=get_admin_main_menu(),
            parse_mode="HTML"
        )
    finally:
        db.close()
    await callback.answer()


# =====================================================
# USER BALANCE, ORDERS, DEPOSITS, PRODUCTS, BAN STATUS
# =====================================================

@router.callback_query(F.data.startswith("user_balance_adjust_"))
async def user_balance_adjust(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Access denied.", show_alert=True)
        return
    user_id = int(callback.data.removeprefix("user_balance_adjust_"))
    await state.set_state(AdminUserBalanceState.waiting_amount)
    await state.update_data(user_id=user_id, mode="adjust")
    await _safe_edit_text(
        callback.message,
        "💰 <b>Adjust Balance</b>\n\nSend an amount:\n"
        "<code>10</code> adds $10\n<code>-5.50</code> removes $5.50\n\n"
        "Maximum 8 decimal places.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="❌ Cancel", callback_data=f"view_user_{user_id}")
        ]])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("user_balance_set_"))
async def user_balance_set(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Access denied.", show_alert=True)
        return
    user_id = int(callback.data.removeprefix("user_balance_set_"))
    await state.set_state(AdminUserBalanceState.waiting_amount)
    await state.update_data(user_id=user_id, mode="set")
    await _safe_edit_text(
        callback.message,
        "✏️ <b>Set Balance</b>\n\nSend the exact new balance, e.g. <code>25.50</code>.\n"
        "Negative balances are not allowed. Maximum 8 decimal places.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="❌ Cancel", callback_data=f"view_user_{user_id}")
        ]])
    )
    await callback.answer()


@router.message(AdminUserBalanceState.waiting_amount)
async def save_user_balance(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await state.clear()
        await message.answer("⛔ Access denied.")
        return
    try:
        amount = Decimal((message.text or "").strip())
        if not amount.is_finite() or max(0, -amount.as_tuple().exponent) > 8:
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        await message.answer("❌ Send a valid amount with at most 8 decimal places.")
        return

    data = await state.get_data()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == data.get("user_id")).first()
        if not user:
            await message.answer("❌ User not found.")
            return
        old_balance = user.balance
        new_balance = amount if data.get("mode") == "set" else user.balance + amount
        if new_balance < Decimal("0"):
            await message.answer(f"❌ Balance cannot be negative. Current: {_money(user.balance)}")
            return
        user.balance = new_balance
        db.commit()
        await message.answer(
            f"✅ <b>Balance updated</b>\n\n👤 {safe(user.full_name)}\n"
            f"Previous: <b>{_money(old_balance)}</b>\nNew: <b>{_money(user.balance)}</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="👤 Open User", callback_data=f"view_user_{user.id}")
            ]])
        )
    finally:
        db.close()
        await state.clear()


@router.callback_query(F.data.startswith("user_orders_"))
async def user_orders(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Access denied.", show_alert=True)
        return
    _, _, user_id, page = callback.data.split("_")
    user_id, page = int(user_id), int(page)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            await callback.answer("User not found.", show_alert=True)
            return
        query = db.query(Order).filter(Order.telegram_id == user.telegram_id).order_by(Order.created_at.desc())
        total = query.count()
        orders = query.offset(page * ACTIVITY_PER_PAGE).limit(ACTIVITY_PER_PAGE).all()
        lines = [f"🛒 <b>Purchase History</b>\n👤 {safe(user.full_name)}\n<i>{total} order(s)</i>\n"]
        for order in orders:
            status = "Refunded" if order.refunded else order.status.replace("_", " ").title()
            lines.append(
                f"<b>#{order.id}</b> {safe(order.product_name)}\n"
                f"Qty: {order.quantity} • {_money(order.amount)}\n"
                f"Status: {safe(status)} • {order.created_at.strftime('%d %b %Y, %H:%M')}\n"
            )
        if not orders:
            lines.append("No purchases found.")
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton(text="⬅ Previous", callback_data=f"user_orders_{user_id}_{page - 1}"))
        if (page + 1) * ACTIVITY_PER_PAGE < total:
            nav.append(InlineKeyboardButton(text="Next ➡", callback_data=f"user_orders_{user_id}_{page + 1}"))
        rows = [nav] if nav else []
        rows.append([InlineKeyboardButton(text="🔙 User Details", callback_data=f"view_user_{user_id}")])
        await _safe_edit_text(callback.message, "\n".join(lines), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    finally:
        db.close()
    await callback.answer()


@router.callback_query(F.data.startswith("user_deposits_"))
async def user_deposits(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Access denied.", show_alert=True)
        return
    _, _, user_id, page = callback.data.split("_")
    user_id, page = int(user_id), int(page)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            await callback.answer("User not found.", show_alert=True)
            return
        query = db.query(Deposit).filter(Deposit.telegram_id == user.telegram_id).order_by(Deposit.created_at.desc())
        total = query.count()
        deposits = query.offset(page * ACTIVITY_PER_PAGE).limit(ACTIVITY_PER_PAGE).all()
        lines = [f"📥 <b>Deposit History</b>\n👤 {safe(user.full_name)}\n<i>{total} deposit(s)</i>\n"]
        for deposit in deposits:
            lines.append(
                f"<b>#{deposit.id}</b> {_money(getattr(deposit, 'amount', Decimal('0')))}\n"
                f"Status: {safe(str(getattr(deposit, 'status', 'completed')).replace('_', ' ').title())} • "
                f"{deposit.created_at.strftime('%d %b %Y, %H:%M')}\n"
            )
        if not deposits:
            lines.append("No deposits found.")
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton(text="⬅ Previous", callback_data=f"user_deposits_{user_id}_{page - 1}"))
        if (page + 1) * ACTIVITY_PER_PAGE < total:
            nav.append(InlineKeyboardButton(text="Next ➡", callback_data=f"user_deposits_{user_id}_{page + 1}"))
        rows = [nav] if nav else []
        rows.append([InlineKeyboardButton(text="🔙 User Details", callback_data=f"view_user_{user_id}")])
        await _safe_edit_text(callback.message, "\n".join(lines), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    finally:
        db.close()
    await callback.answer()


@router.callback_query(F.data.startswith("user_products_"))
async def user_products(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Access denied.", show_alert=True)
        return
    user_id = int(callback.data.removeprefix("user_products_"))
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            await callback.answer("User not found.", show_alert=True)
            return
        products = db.query(
            Order.product_name,
            func.count(Order.id).label("purchases"),
            func.coalesce(func.sum(Order.quantity), 0).label("quantity"),
            func.coalesce(func.sum(Order.amount), 0).label("paid"),
        ).filter(
            Order.telegram_id == user.telegram_id,
            Order.refunded.is_(False),
        ).group_by(Order.product_name).order_by(func.sum(Order.amount).desc()).all()
        lines = [f"📦 <b>Purchased Products</b>\n👤 {safe(user.full_name)}\n"]
        for product in products:
            lines.append(f"• <b>{safe(product.product_name)}</b>\n  Purchases: {product.purchases} • Qty: {product.quantity} • Paid: {_money(product.paid)}")
        if not products:
            lines.append("No completed product purchases found.")
        await _safe_edit_text(
            callback.message,
            "\n".join(lines),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🛒 Purchase History", callback_data=f"user_orders_{user_id}_0")],
                [InlineKeyboardButton(text="🔙 User Details", callback_data=f"view_user_{user_id}")],
            ])
        )
    finally:
        db.close()
    await callback.answer()


@router.callback_query(F.data.startswith("user_ban_"))
async def user_ban_toggle(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Access denied.", show_alert=True)
        return
    user_id = int(callback.data.removeprefix("user_ban_"))
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            await callback.answer("User not found.", show_alert=True)
            return
        user.is_banned = not user.is_banned
        db.commit()
        status = "🚫 User banned." if user.is_banned else "✅ User unbanned."
        user_name = safe(user.full_name)
    finally:
        db.close()
    await _safe_edit_text(
        callback.message,
        f"<b>{status}</b>\n\n👤 {user_name}\n"
        "The database status has been updated.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="👤 Back to User Details", callback_data=f"view_user_{user_id}")
        ]]),
    )
    await callback.answer(status, show_alert=True)