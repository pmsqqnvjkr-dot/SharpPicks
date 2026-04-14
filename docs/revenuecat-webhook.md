# RevenueCat Webhook Integration

## Endpoint

```
POST https://app.sharppicks.ai/api/webhooks/revenuecat
```

## Authentication

Bearer token in the `Authorization` header, validated against the `REVENUECAT_WEBHOOK_SECRET` environment variable on Railway.

## Setup

### 1. Generate the shared secret

```bash
openssl rand -hex 32
```

### 2. Set the env var on Railway

Add `REVENUECAT_WEBHOOK_SECRET=<generated_secret>` to the Railway service environment variables.

### 3. Configure in RevenueCat dashboard

1. Go to **Project Settings → Integrations → Webhooks**
2. Set **Webhook URL**: `https://app.sharppicks.ai/api/webhooks/revenuecat`
3. Set **Authorization header**: `Bearer <same_secret>`
4. Enable events: INITIAL_PURCHASE, RENEWAL, CANCELLATION, EXPIRATION, BILLING_ISSUE, PRODUCT_CHANGE, UNCANCELLATION

### 4. Test

Use RevenueCat's **"Send Test Event"** button on the webhook configuration page. Check Railway logs for `RevenueCat webhook:` entries.

## Events Handled

| Event | Action |
|-------|--------|
| `INITIAL_PURCHASE` | `is_premium=True`, `subscription_status='active'`, `pro_source='revenuecat'`, set `current_period_end` |
| `RENEWAL` | Same as INITIAL_PURCHASE — refreshes expiration |
| `PRODUCT_CHANGE` | Same — updates plan (monthly/annual) based on `product_id` |
| `UNCANCELLATION` | Same — reactivates Pro |
| `EXPIRATION` | `is_premium=False`, `subscription_status='expired'` |
| `CANCELLATION` | Logged only — user retains access until `current_period_end` |
| `BILLING_ISSUE` | Sets `subscription_status='past_due'`, admin alerted |

## User Matching

RevenueCat `app_user_id` maps to the SharpPicks `user.id` (UUID). This is set in the iOS app via `Purchases.logIn({ appUserID: userId })` on authentication.

## Idempotency

Uses the existing `ProcessedEvent` table. Each `event.id` is stored on first processing; duplicates return `200 { duplicate: true }` without re-processing.

## Monitoring

- **Railway logs**: Search for `RevenueCat webhook:` or `RevenueCat:` prefixed entries
- **RevenueCat dashboard**: Webhooks → Delivery History shows request/response for each event
- **Admin alerts**: The app sends push notifications to admin users on all Pro status changes

## Payload Reference

```json
{
  "api_version": "1.0",
  "event": {
    "id": "evt_unique_id",
    "type": "INITIAL_PURCHASE",
    "app_user_id": "user-uuid-from-app",
    "product_id": "pro_yearly",
    "entitlement_ids": ["pro"],
    "expiration_at_ms": 1700000000000,
    "purchased_at_ms": 1699000000000,
    "store": "APP_STORE",
    "environment": "PRODUCTION"
  }
}
```
