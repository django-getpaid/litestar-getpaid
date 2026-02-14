"""Success/failure redirect routes."""

from typing import Annotated

from getpaid_core.protocols import PaymentRepository
from litestar import Controller, get
from litestar.params import Dependency
from litestar.response import Redirect

from litestar_getpaid.config import GetpaidConfig
from litestar_getpaid.exceptions import PaymentNotFoundError


class RedirectController(Controller):
    """Success/failure redirect endpoints."""

    tags = ["redirects"]

    @get("/success/{payment_id:str}")
    async def success_redirect(
        self,
        payment_id: str,
        config: Annotated[GetpaidConfig, Dependency(skip_validation=True)],
        repository: Annotated[
            PaymentRepository, Dependency(skip_validation=True)
        ],
    ) -> Redirect:
        """Redirect user to success URL after payment."""
        try:
            await repository.get_by_id(payment_id)
        except KeyError as exc:
            raise PaymentNotFoundError(payment_id) from exc
        sep = "&" if "?" in config.success_url else "?"
        url = f"{config.success_url}{sep}payment_id={payment_id}"
        return Redirect(path=url)

    @get("/failure/{payment_id:str}")
    async def failure_redirect(
        self,
        payment_id: str,
        config: Annotated[GetpaidConfig, Dependency(skip_validation=True)],
        repository: Annotated[
            PaymentRepository, Dependency(skip_validation=True)
        ],
    ) -> Redirect:
        """Redirect user to failure URL after payment."""
        try:
            await repository.get_by_id(payment_id)
        except KeyError as exc:
            raise PaymentNotFoundError(payment_id) from exc
        sep = "&" if "?" in config.failure_url else "?"
        url = f"{config.failure_url}{sep}payment_id={payment_id}"
        return Redirect(path=url)
