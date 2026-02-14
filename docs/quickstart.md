# Quick start

## Installation

Install litestar-getpaid with the SQLAlchemy extras:

```bash
pip install litestar-getpaid[sqlalchemy]
```

Or with uv:

```bash
uv add litestar-getpaid --extra sqlalchemy
```

## Minimal example

Below is a complete working example that sets up payment processing with
SQLAlchemy as the storage backend.

```python
from litestar import Litestar
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from litestar_getpaid.config import GetpaidConfig
from litestar_getpaid.contrib.sqlalchemy.models import Base
from litestar_getpaid.contrib.sqlalchemy.repository import (
    SQLAlchemyPaymentRepository,
)
from litestar_getpaid.contrib.sqlalchemy.retry_store import SQLAlchemyRetryStore
from litestar_getpaid.protocols import Order, OrderResolver
from litestar_getpaid.plugin import create_payment_router

# --- Configuration ---

config = GetpaidConfig(
    default_backend="dummy",
    success_url="https://example.com/thank-you",
    failure_url="https://example.com/payment-failed",
    backends={
        "dummy": {
            "module": "getpaid_core.backends.dummy",
        },
    },
)

# --- Database setup ---

engine = create_async_engine("sqlite+aiosqlite:///payments.db")
session_factory = async_sessionmaker(engine, expire_on_commit=False)


# --- Order resolver ---

class SimpleOrderResolver:
    """Example order resolver.

    In a real application this would load an order from your database.
    """

    async def resolve(self, order_id: str) -> Order:
        # Return an object satisfying the Order protocol.
        # See the example app for a full implementation.
        raise NotImplementedError("Implement order lookup here")


# --- Build the app ---

repository = SQLAlchemyPaymentRepository(session_factory)
retry_store = SQLAlchemyRetryStore(session_factory)

payment_router = create_payment_router(
    config=config,
    repository=repository,
    order_resolver=SimpleOrderResolver(),
    retry_store=retry_store,
)

app = Litestar(route_handlers=[payment_router])
```

## Running the app

Create the database tables (e.g. using an Alembic migration or a startup
event) and start the server:

```bash
litestar run --reload
```

Or with uvicorn directly:

```bash
uvicorn myapp:app --reload
```

The payment endpoints will be available under `/payments/`.

## Example application

A full working example application is included in the
[`example/`](https://github.com/django-getpaid/litestar-getpaid/tree/main/example)
directory of this repository. It includes:

- An order management UI with Jinja2 templates
- A **fake payment gateway simulator** (paywall) that lets you approve or
  reject payments interactively
- SQLAlchemy async storage with automatic table creation
- Full payment lifecycle: create order, initiate payment, authorize at
  gateway, receive callback, view result

To run it:

```bash
cd example
uv sync
uv run litestar run --reload
```

Then open `http://127.0.0.1:8000` in your browser.

## Next steps

- {doc}`configuration` — all available settings and environment variables
- {doc}`api` — full API reference (protocols, schemas, endpoints)
