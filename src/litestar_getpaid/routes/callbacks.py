"""Gateway callback handling routes."""

import logging
from typing import Annotated

from getpaid_core.exceptions import CommunicationError, InvalidCallbackError
from getpaid_core.flow import PaymentFlow
from getpaid_core.protocols import PaymentRepository
from litestar import Controller, Request, Response, post
from litestar.params import Dependency

from litestar_getpaid.config import GetpaidConfig
from litestar_getpaid.exceptions import PaymentNotFoundError
from litestar_getpaid.protocols import CallbackRetryStore

logger = logging.getLogger(__name__)


class CallbackController(Controller):
    """Gateway callback endpoints."""

    tags = ["callbacks"]

    @post("/callback/{payment_id:str}")
    async def handle_callback(
        self,
        request: Request,
        payment_id: str,
        data: dict,
        config: Annotated[GetpaidConfig, Dependency(skip_validation=True)],
        repository: Annotated[
            PaymentRepository, Dependency(skip_validation=True)
        ],
        retry_store: Annotated[
            CallbackRetryStore | None, Dependency(skip_validation=True)
        ] = None,
    ) -> Response:
        """Handle a PUSH callback from a payment gateway."""
        try:
            payment = await repository.get_by_id(payment_id)
        except KeyError as exc:
            raise PaymentNotFoundError(payment_id) from exc

        flow = PaymentFlow(
            repository=repository,
            config=config.backends,
        )

        raw_body = await request.body()
        callback_headers = dict(request.headers)

        try:
            await flow.handle_callback(
                payment=payment,
                data=data,
                headers=callback_headers,
                raw_body=raw_body,
            )
        except InvalidCallbackError:
            raise
        except CommunicationError as exc:
            if retry_store is not None:
                retry_payload = dict(data)
                retry_payload["_raw_body"] = raw_body.decode("utf-8")
                await retry_store.store_failed_callback(
                    payment_id=payment_id,
                    payload=retry_payload,
                    headers=callback_headers,
                )
                logger.warning(
                    "Callback for payment %s failed, queued for retry: %s",
                    payment_id,
                    exc,
                )
            return Response(
                content={
                    "detail": str(exc),
                    "code": "callback_failed",
                },
                status_code=502,
            )

        return Response(content={"status": "ok"}, status_code=200)
