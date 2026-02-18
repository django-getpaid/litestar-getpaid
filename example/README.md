# litestar-getpaid Example

A fully working Litestar web application demonstrating payment processing
with `litestar-getpaid` and multiple payment backends (DummyProcessor, PayU, Paynow).

## Features

- Multiple payment backends with environment variable configuration
- Order creation and management UI
- Payment processing via litestar-getpaid REST API
- Fake payment gateway simulator (paywall) for interactive testing
- Comprehensive error handling for payment failures
- SQLAlchemy with SQLite database

## Payment flow

1. User creates an order on the home page.
2. User clicks **Pay** on the order detail page.
3. The app calls the litestar-getpaid REST API to create a payment.
4. The app registers the payment with the fake gateway (paywall).
5. User is redirected to the paywall authorization page.
6. User approves or rejects the payment.
7. The paywall sends a callback to the litestar-getpaid callback endpoint.
8. The payment status is updated via the FSM.
9. User is redirected back to the order detail page.

## Running

### Quick start (with DummyProcessor)

```bash
uv sync
uv run uvicorn app:app --reload --port 8001
```

Then open <http://127.0.0.1:8001> in your browser.

### Running with PayU backend

```bash
export GETPAID_DEFAULT_BACKEND=payu
export PAYU_POS_ID=300746
export PAYU_SECOND_KEY=b6ca15b0d1020e8094d9b5f8d163db54
export PAYU_OAUTH_ID=300746
export PAYU_OAUTH_SECRET=2ee86a66e5d97e3fadc400c9f19b065d

uv run uvicorn app:app --reload --port 8001
```

### Running with Paynow backend

```bash
export GETPAID_DEFAULT_BACKEND=paynow
export PAYNOW_API_KEY=d2e1d881-40b0-4b7e-9168-181bae3dc4e0
export PAYNOW_SIGNATURE_KEY=8e42a868-5562-440d-817c-4921632fb049

uv run uvicorn app:app --reload --port 8001
```

## Configuration

The app supports the following environment variables:

### Backend selection

- `GETPAID_DEFAULT_BACKEND`: Backend to use (`dummy`, `payu`, or `paynow`). Default: `dummy`

### PayU credentials (PLN sandbox)

- `PAYU_POS_ID`: POS ID. Default: `300746`
- `PAYU_SECOND_KEY`: MD5 second key. Default: `b6ca15b0d1020e8094d9b5f8d163db54`
- `PAYU_OAUTH_ID`: OAuth client ID. Default: `300746`
- `PAYU_OAUTH_SECRET`: OAuth client secret. Default: `2ee86a66e5d97e3fadc400c9f19b065d`

### Paynow credentials (sandbox)

- `PAYNOW_API_KEY`: API key. Default: `d2e1d881-40b0-4b7e-9168-181bae3dc4e0`
- `PAYNOW_SIGNATURE_KEY`: Signature key. Default: `8e42a868-5562-440d-817c-4921632fb049`

**Note:** The default values are sandbox credentials for testing purposes only.

## Structure

| File | Description |
|---|---|
| `app.py` | Main Litestar application with order views and payment backends |
| `models.py` | SQLAlchemy Order and PaywallEntry models |
| `paywall.py` | Fake payment gateway simulator |
| `templates/` | Jinja2 templates using the Tabler UI framework |

## Security notice

> **Warning:** This example app is for demonstration purposes only. It does
> not include CSRF protection, authentication, or other security measures
> required in a production deployment. The sandbox credentials are hardcoded
> as defaults for convenience but should be stored securely in production.
