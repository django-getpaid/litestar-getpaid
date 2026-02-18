# litestar-getpaid

[![PyPI version](https://img.shields.io/pypi/v/litestar-getpaid)](https://pypi.org/project/litestar-getpaid/)
[![Python version](https://img.shields.io/pypi/pyversions/litestar-getpaid)](https://pypi.org/project/litestar-getpaid/)
[![Litestar version](https://img.shields.io/badge/Litestar-2.0%2B-202235)](https://litestar.dev/)
[![License](https://img.shields.io/pypi/l/litestar-getpaid)](https://github.com/django-getpaid/python-getpaid/blob/main/litestar-getpaid/LICENSE)

**Async-native payment processing wrapper for Litestar.**

`litestar-getpaid` is a thin but powerful wrapper around [getpaid-core](https://github.com/django-getpaid/python-getpaid-core), designed specifically for the Litestar framework. It provides a ready-to-use REST API for creating payments, handling callbacks, and managing redirects, all while staying fully asynchronous.

> **v3.0.0a2 (Alpha)** — This is a pre-release. The API follows the major v3 overhaul of the Getpaid ecosystem.

## Features

- **Async-native**: Built from the ground up to leverage Python's `async/await` and Litestar's high-performance architecture.
- **Multi-backend**: Process payments through multiple providers (PayU, Paynow, Przelewy24, etc.) simultaneously.
- **Pluggable Persistence**: Includes optional SQLAlchemy 2.0 async support out of the box.
- **Retry Mechanism**: Robust webhook callback retry system with exponential backoff.
- **Typed Configuration**: Configuration managed via Pydantic, supporting environment variables.
- **REST API**: Standardized endpoints for payment lifecycle management.

## Installation

```bash
pip install litestar-getpaid
```

If you want to use the built-in SQLAlchemy support:

```bash
pip install litestar-getpaid[sqlalchemy]
```

## Quick Start

### 1. Define your Order Resolver

Litestar-getpaid needs to know how to find your orders. Implement the `OrderResolver` protocol:

```python
from models import Order

class MyOrderResolver:
    async def resolve(self, order_id: str) -> Order:
        # Fetch your order from database
        async with session_factory() as session:
            order = await session.get(Order, order_id)
            if not order:
                raise KeyError(f"Order {order_id} not found")
            return order
```

### 2. Configure and Mount the Router

```python
from litestar import Litestar
from litestar_getpaid.config import GetpaidConfig
from litestar_getpaid.plugin import create_payment_router
from litestar_getpaid.contrib.sqlalchemy.repository import SQLAlchemyPaymentRepository

config = GetpaidConfig(
    default_backend="dummy",
    backends={
        "dummy": {"module": "getpaid_core.backends.dummy"},
        "payu": {
            "module": "getpaid_payu",
            "pos_id": "12345",
            "second_key": "secret",
            # ... other PayU settings
        },
    },
)

payment_router = create_payment_router(
    config=config,
    repository=SQLAlchemyPaymentRepository(session_factory),
    order_resolver=MyOrderResolver(),
)

app = Litestar(route_handlers=[payment_router])
```

## Async Patterns

Everything in `litestar-getpaid` is `async`. When you call the payment endpoints, the underlying `getpaid-core` processors are executed asynchronously.

The callback system uses a background task worker (compatible with Litestar's lifespan) to ensure that even if your payment provider's webhook fails, it will be retried without blocking your main application.

## Example App

Check out the [comprehensive example app](https://github.com/django-getpaid/python-getpaid/tree/main/litestar-getpaid/example) in this repository. It demonstrates:

- **Multiple Backends**: Simultaneous configuration of Dummy, PayU, and Paynow.
- **Sandbox Mode**: Testing with real provider sandboxes.
- **Custom UI**: A simple Jinja2-based dashboard for managing orders and payments.
- **Paywall Simulator**: A built-in simulator for testing the full redirect flow without leaving your local environment.

To run it:

```bash
cd litestar-getpaid/example
uv sync
uv run python app.py
```

## Getpaid Ecosystem

`litestar-getpaid` is part of a larger ecosystem:

- **Core**: [python-getpaid-core](https://github.com/django-getpaid/python-getpaid-core)
- **Wrappers**: [django-getpaid](https://github.com/django-getpaid/django-getpaid), [fastapi-getpaid](https://github.com/django-getpaid/fastapi-getpaid)
- **Processors**: 
    - [getpaid-payu](https://github.com/django-getpaid/python-getpaid-payu)
    - [getpaid-paynow](https://github.com/django-getpaid/python-getpaid-paynow)
    - [getpaid-bitpay](https://github.com/django-getpaid/python-getpaid-bitpay)
    - [getpaid-przelewy24](https://github.com/django-getpaid/python-getpaid-przelewy24)

## License

This project is licensed under the MIT License.

