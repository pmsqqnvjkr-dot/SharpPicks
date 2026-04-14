# RevenueCat Webhook Integration

## Endpoint

```
POST /api/webhooks/revenuecat
```

## Authentication

Bearer token in `Authorization` header. Set the shared secret in:
- **RevenueCat dashboard:** Project → Integrations → Webhooks → Authorization header
- **Backend env:** `REVENUECAT_WEBHOOK_SECRET`

```python
auth = request.headers.get('Authorization', '')
if auth != f'Bearer {os.environ["REVENUECAT_WEBHOOK_SECRET"]}':
    return jsonify({'error': 'Unauthorized'}), 401
```

## Events to Handle

| Event | Action |
|-------|--------|
| `INITIAL_PURCHASE` | Set `user.is_premium = True`, set `pro_expires_at` from expiration date |
| `RENEWAL` | Update `pro_expires_at` with new expiration |
| `CANCELLATION` | Leave `is_premium = True` until expiration, log cancellation date |
| `EXPIRATION` | Set `user.is_premium = False`, `subscription_status = 'expired'` |
| `BILLING_ISSUE` | Flag user, optionally send email about payment failure |
| `PRODUCT_CHANGE` | Update `subscription_plan` to new product identifier |

## User Matching

RevenueCat sends `app_user_id` in the webhook payload. This maps to the SharpPicks `user.id` (set via `Purchases.logIn({ appUserID: userId })` in the app).

```python
app_user_id = event.get('app_user_id')
user = db.session.get(User, app_user_id)
```

## Payload Structure

```json
{
  "api_version": "1.0",
  "event": {
    "id": "evt_unique_id",
    "type": "INITIAL_PURCHASE",
    "app_user_id": "user_id_from_app",
    "product_id": "pro_yearly",
    "entitlement_ids": ["pro"],
    "expiration_at_ms": 1700000000000,
    "purchased_at_ms": 1699000000000,
    "store": "APP_STORE",
    "environment": "PRODUCTION"
  }
}
```

## Idempotency

Deduplicate by `event.id`. Store processed event IDs and skip duplicates.

## Response

Return `200 OK` within 5 seconds or RevenueCat will retry (up to 5 times with exponential backoff).

```python
return jsonify({'success': True}), 200
```

## RevenueCat Dashboard Setup

1. Go to **Project Settings → Integrations → Webhooks**
2. Set URL: `https://app.sharppicks.ai/api/webhooks/revenuecat`
3. Set Authorization header: `Bearer <your-secret>`
4. Enable events: INITIAL_PURCHASE, RENEWAL, CANCELLATION, EXPIRATION, BILLING_ISSUE, PRODUCT_CHANGE
