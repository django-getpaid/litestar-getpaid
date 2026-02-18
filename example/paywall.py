"""Fake payment gateway simulator (paywall).

Simulates a real payment broker for demonstration purposes:
- Register payment via REST API
- Display authorization form to the user
- Send callback to the payment system on approval/rejection
- Redirect user to success/failure URL
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Annotated

import httpx
from litestar import Request, Router, get, post
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.response import Redirect, Template
from models import PaywallEntry
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)

# Will be set by the app on startup.
session_factory: async_sessionmaker[AsyncSession] | None = None


def configure(sf: async_sessionmaker[AsyncSession]) -> None:
    """Set the session factory for the paywall module."""
    global session_factory  # noqa: PLW0603
    session_factory = sf


def _get_session_factory() -> async_sessionmaker[AsyncSession]:
    if session_factory is None:
        raise RuntimeError("Paywall session_factory not configured")
    return session_factory


@post("/register")
async def register_payment(request: Request) -> dict:
    """REST endpoint: register a payment and return the gateway URL.

    Accepts JSON body with:
        ext_id, value, currency, description, callback,
        success_url, failure_url
    """
    data = await request.json()
    legal_fields = {
        "ext_id",
        "value",
        "currency",
        "description",
        "callback",
        "success_url",
        "failure_url",
    }
    params = {k: v for k, v in data.items() if k in legal_fields}
    if "value" in params:
        params["value"] = Decimal(str(params["value"]))

    sf = _get_session_factory()
    async with sf() as session:
        entry = PaywallEntry(**params)
        session.add(entry)
        await session.commit()
        await session.refresh(entry)
        entry_id = entry.id

    gateway_url = (
        str(request.url_for("paywall_gateway_page")) + f"?pay_id={entry_id}"
    )
    return {"url": gateway_url}


@get("/gateway", name="paywall_gateway_page")
async def paywall_gateway(
    request: Request,
    pay_id: str | None = None,
) -> Template:
    """Display the fake gateway authorization page."""
    context: dict = {}

    if pay_id:
        sf = _get_session_factory()
        async with sf() as session:
            entry = await session.get(PaywallEntry, pay_id)
        if entry:
            context.update(
                {
                    "ext_id": entry.ext_id,
                    "value": entry.value,
                    "currency": entry.currency,
                    "description": entry.description,
                    "callback": entry.callback,
                    "success_url": entry.success_url,
                    "failure_url": entry.failure_url,
                    "message": "Presenting pre-registered payment",
                }
            )
        else:
            context["message"] = "Payment entry not found"
    else:
        context.update(
            {
                "ext_id": request.query_params.get("ext_id", ""),
                "value": request.query_params.get("value", ""),
                "currency": request.query_params.get("currency", ""),
                "description": request.query_params.get("description", ""),
                "callback": request.query_params.get("callback", ""),
                "success_url": request.query_params.get("success_url", ""),
                "failure_url": request.query_params.get("failure_url", ""),
                "message": "Presenting directly requested payment",
            }
        )

    return Template(template_name="paywall_gateway.html", context=context)


@dataclass
class AuthorizeForm:
    """Form data for the paywall authorization form."""

    authorize_payment: str
    callback: str = ""
    success_url: str = ""
    failure_url: str = ""


@post("/authorize")
async def paywall_authorize(
    request: Request,
    data: Annotated[
        AuthorizeForm,
        Body(media_type=RequestEncodingType.URL_ENCODED),
    ],
) -> Redirect:
    """Handle the authorization form submission.

    Sends a callback to the payment system and redirects the user.
    """
    if data.callback:
        # Build absolute URL if callback is relative.
        if data.callback.startswith("/"):
            callback_url = str(request.base_url).rstrip("/") + data.callback
        else:
            callback_url = data.callback

        if data.authorize_payment == "1":
            # Approved: send confirm_payment FSM trigger via callback.
            async with httpx.AsyncClient() as client:
                await client.post(
                    callback_url,
                    json={"new_status": "confirm_payment"},
                )
            return Redirect(path=data.success_url, status_code=303)
        else:
            # Rejected: send fail FSM trigger via callback.
            async with httpx.AsyncClient() as client:
                await client.post(
                    callback_url,
                    json={"new_status": "fail"},
                )
            return Redirect(path=data.failure_url, status_code=303)

    # No callback configured -- just redirect.
    if data.authorize_payment == "1":
        return Redirect(path=data.success_url or "/", status_code=303)
    return Redirect(path=data.failure_url or "/", status_code=303)


@get("/status/{entry_id:str}")
async def paywall_status(entry_id: str) -> dict:
    """Get the status of a paywall entry."""
    sf = _get_session_factory()
    async with sf() as session:
        entry = await session.get(PaywallEntry, entry_id)
    if entry is None:
        return {"detail": "Entry not found"}
    return {
        "payment_status": entry.payment_status,
        "fraud_status": entry.fraud_status,
    }


paywall_router = Router(
    path="/paywall",
    route_handlers=[
        register_payment,
        paywall_gateway,
        paywall_authorize,
        paywall_status,
    ],
)
