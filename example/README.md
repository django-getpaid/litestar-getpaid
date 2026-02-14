# litestar-getpaid Example

A fully working Litestar web application demonstrating payment processing
with `litestar-getpaid` and a fake payment gateway simulator.

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

```bash
uv sync
uv run uvicorn app:app --reload --port 8001
```

Then open <http://127.0.0.1:8001> in your browser.

## Structure

| File | Description |
|---|---|
| `app.py` | Main Litestar application with order views |
| `models.py` | SQLAlchemy Order and PaywallEntry models |
| `paywall.py` | Fake payment gateway simulator |
| `templates/` | Jinja2 templates using the Tabler UI framework |

> **Note:** This example app is for demonstration purposes only. It does
> not include CSRF protection, authentication, or other security measures
> required in a production deployment.
