# API reference

## Router factory

### `create_payment_router()`

```python
from litestar_getpaid.plugin import create_payment_router

create_payment_router(
    *,
    config: GetpaidConfig,
    repository: PaymentRepository,
    registry: LitestarPluginRegistry | None = None,
    order_resolver: OrderResolver | None = None,
    retry_store: CallbackRetryStore | None = None,
) -> Router
```

Creates and returns a fully configured Litestar `Router` with all payment
endpoints. Accepts the configuration, a payment repository, and optional
components (plugin registry, order resolver, retry store).

Dependencies are injected into Controllers via Litestar's `Provide()` DI system.

## Configuration

### `GetpaidConfig`

```python
from litestar_getpaid.config import GetpaidConfig
```

Pydantic settings model for all payment configuration. See
{doc}`configuration` for the full list of fields.

## Protocols

### `PaymentWithHelpers`

```python
from litestar_getpaid.protocols import PaymentWithHelpers
```

Extends the core `Payment` protocol with `is_fully_paid()` and
`is_fully_refunded()` helper methods required by the FSM guards.

### `OrderResolver`

```python
from litestar_getpaid.protocols import OrderResolver
```

Protocol for resolving an `order_id` string into an `Order` object.
Implementations must provide an async `resolve(order_id: str) -> Order`
method.

### `CallbackRetryStore`

```python
from litestar_getpaid.protocols import CallbackRetryStore
```

Storage abstraction for the webhook retry queue. Methods:

- `store_failed_callback(payment_id, payload, headers) -> str`
- `get_due_retries(limit=10) -> list[dict]`
- `mark_succeeded(retry_id) -> None`
- `mark_failed(retry_id, error) -> None`
- `mark_exhausted(retry_id) -> None`

## Plugin registry

### `LitestarPluginRegistry`

```python
from litestar_getpaid.registry import LitestarPluginRegistry
```

Wraps the core `PluginRegistry` and adds support for registering
per-backend `Router` instances for custom callback routes.

## Controllers

### `PaymentController`

```python
from litestar_getpaid.routes.payments import PaymentController
```

Litestar Controller at `/payments` providing payment CRUD endpoints:
create, get by ID, and list by order.

### `CallbackController`

```python
from litestar_getpaid.routes.callbacks import CallbackController
```

Litestar Controller handling gateway PUSH callbacks at `/callback/{payment_id}`.
Failed callbacks are queued for retry when a `CallbackRetryStore` is configured.

### `RedirectController`

```python
from litestar_getpaid.routes.redirects import RedirectController
```

Litestar Controller providing success and failure redirect endpoints at
`/success/{payment_id}` and `/failure/{payment_id}`.

## Exceptions

### `PaymentNotFoundError`

```python
from litestar_getpaid.exceptions import PaymentNotFoundError
```

Raised when a payment lookup fails. Automatically mapped to a
`404 Not Found` HTTP response by the registered exception handlers.

## SQLAlchemy contrib

The `litestar_getpaid.contrib.sqlalchemy` package provides ready-to-use
async models and implementations.

### `PaymentModel`

```python
from litestar_getpaid.contrib.sqlalchemy.models import PaymentModel
```

SQLAlchemy 2.0 mapped model implementing the `PaymentWithHelpers` protocol.
Table name: `getpaid_payment`.

### `CallbackRetryModel`

```python
from litestar_getpaid.contrib.sqlalchemy.models import CallbackRetryModel
```

SQLAlchemy model for the webhook callback retry queue.
Table name: `getpaid_callback_retry`.

### `SQLAlchemyPaymentRepository`

```python
from litestar_getpaid.contrib.sqlalchemy.repository import (
    SQLAlchemyPaymentRepository,
)
```

Async `PaymentRepository` implementation backed by SQLAlchemy sessions.
Accepts an `async_sessionmaker` and provides `get_by_id`, `create`, `save`,
`update_status`, and `list_by_order` methods.

### `SQLAlchemyRetryStore`

```python
from litestar_getpaid.contrib.sqlalchemy.retry_store import (
    SQLAlchemyRetryStore,
)
```

`CallbackRetryStore` implementation backed by SQLAlchemy. Handles
exponential backoff scheduling and retry lifecycle management.

## Schemas

### Request schemas

`CreatePaymentRequest`
: Fields: `order_id`, `backend`, `amount`, `currency`, `description` (optional).

### Response schemas

`CreatePaymentResponse`
: Fields: `payment_id`, `redirect_url`, `method`, `form_data`.

`PaymentResponse`
: Full payment data including amounts, status, backend, and fraud fields.

`PaymentListResponse`
: Paginated response with `items: list[PaymentResponse]` and `total: int`.

`ErrorResponse`
: Standard error body with `detail` and `code` fields.

`CallbackRetryResponse`
: Retry status with `id`, `payment_id`, `attempts`, `status`, `last_error`.

## REST endpoints

The `create_payment_router()` factory returns a Litestar `Router` with
the following endpoints. Mount it at any path by including it in your
app's `route_handlers` (directly, or nested inside another `Router`).

| Method | Path                       | Description                          |
|--------|----------------------------|--------------------------------------|
| GET    | `/payments/`               | List payments for an order (`?order_id=...`) |
| POST   | `/payments/`               | Create a new payment                 |
| GET    | `/payments/{payment_id}`   | Get a single payment by ID           |
| POST   | `/callback/{payment_id}`   | Handle a PUSH callback from a gateway |
| GET    | `/success/{payment_id}`    | Redirect to the configured success URL |
| GET    | `/failure/{payment_id}`    | Redirect to the configured failure URL |
