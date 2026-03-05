# SharpPicks Pre-App Store Test Checklist

Run before submitting to the App Store. Use this checklist to validate all critical flows.

---

## 1. Core User Flows

### Sign up → email verification → onboarding
- [ ] Create new account with valid email
- [ ] Receive verification email
- [ ] Click verification link and land in app
- [ ] Complete onboarding flow
- [ ] See picks/dashboard after onboarding

### Free → Pro upgrade (Stripe checkout)
- [ ] Tap upgrade on free account
- [ ] Redirects to Stripe Checkout
- [ ] Complete test payment (card 4242 4242 4242 4242)
- [ ] Return to app with Pro status
- [ ] Premium content (picks) visible

### 14-day trial start and expiry
- [ ] Start trial (new user or trial button)
- [ ] Trial badge/date shown in UI
- [ ] After 14 days (or manually trigger cron): user downgrades to free
- [ ] Premium content locked after expiry

### Password reset email
- [ ] Request password reset
- [ ] Receive email with reset link
- [ ] Click link, set new password
- [ ] Log in with new password

### Account deletion
- [ ] Request account deletion (if available)
- [ ] Confirmation flow works
- [ ] Account fully removed from system

---

## 2. Pick Experience

### Pick card displays correctly
- [ ] Side, spread, edge % visible
- [ ] All values match backend data
- [ ] Card layout correct on mobile and desktop

### Pass day displays correctly
- [ ] "No action today" or pass message shows
- [ ] Games analyzed count correct

### Outcome review after game ends
- [ ] Pick graded (win/loss/push)
- [ ] Result visible on card
- [ ] PnL/record updated

### Pick history / audit trail loads
- [ ] History tab or list loads
- [ ] Past picks with results visible
- [ ] No infinite loading or errors

### CLV display after closing line
- [ ] Closing line value shown when available
- [ ] CLV calculated correctly (positive/negative)

---

## 3. Notifications

### Push on pick day
- [ ] Push received when pick published
- [ ] Title/body correct
- [ ] Tap opens app to picks tab

### Push on pass day
- [ ] Push received when pass day
- [ ] Message correct

### Push on result grade
- [ ] Push received when pick graded
- [ ] Win/Loss/Push reflected in copy

### Email backup
- [ ] Email received for pick day
- [ ] Email received for pass day
- [ ] Email received for result

---

## 4. Payments

### Stripe checkout completes
- [ ] Checkout session creates
- [ ] Payment succeeds
- [ ] User upgraded in DB

### Webhook updates subscription status
- [ ] `checkout.session.completed` → user active/trial
- [ ] `subscription.updated` (canceled) → downgrade
- [ ] `subscription.deleted` → downgrade
- [ ] `invoice.paid` → active
- [ ] `invoice.payment_failed` → past_due or handled

### Trial expiry downgrades correctly
- [ ] `expire_trials` cron runs
- [ ] Expired trial users: `subscription_status=expired`, `is_premium=False`
- [ ] Frontend shows free tier after refresh

### Cancel anytime works
- [ ] User cancels subscription
- [ ] Access until period end
- [ ] After period end: downgraded

### Founding member rate locks in
- [ ] Founding member plan shows locked price
- [ ] Renewal keeps founding rate

---

## 5. Auth & Security

### Sign in / sign out
- [ ] Sign in with email + password
- [ ] Sign out clears session
- [ ] Token invalid after logout

### Session expiry
- [ ] Long idle → re-auth required
- [ ] Remember me extends session

### Invalid login handling
- [ ] Wrong password → 401
- [ ] Lockout after 5 failed attempts
- [ ] Lockout message shows remaining time

### JWT or session tokens working
- [ ] Bearer token auth works for API
- [ ] Cookie-based session works for web

---

## 6. App Store Specific

### App loads without white screen
- [ ] Cold start shows splash or content quickly
- [ ] No prolonged white/blank screen

### No crashes on first launch
- [ ] Fresh install launches
- [ ] No crash on iOS/Android/Web

### Privacy policy URL works
- [ ] Link opens correct page
- [ ] Content renders

### Terms of service URL works
- [ ] Link opens correct page
- [ ] Content renders

### App icon all sizes present
- [ ] 192x192, 512x512, etc. in manifest
- [ ] Icons display correctly

### Splash screen looks correct
- [ ] No distortion
- [ ] Branding correct

### No console errors on launch
- [ ] Dev tools console clean
- [ ] No uncaught exceptions

---

## 7. Most Likely Problem Areas

### Trial expiry → downgrade flow
- [ ] Run `/api/cron/expire-trials` with test user past trial_end
- [ ] Verify user downgraded
- [ ] Verify frontend reflects change after auth refresh

### Stripe webhook subscription status sync
- [ ] Use Stripe CLI to send test webhooks
- [ ] Verify DB updates match expected status

### Deep links from push notifications
- [ ] Tap pick notification → opens picks tab
- [ ] Tap weekly summary → opens profile/weekly
- [ ] App opens from background/closed state

---

## Automated Tests

Run pytest before submission (env vars are set automatically by conftest):

```bash
TESTING=1 python -m pytest tests/ -v
```

Or with explicit vars if running in CI:

```bash
TESTING=1 CRON_SECRET=test-cron-secret STRIPE_LIVE_SECRET_KEY=sk_test_fake python -m pytest tests/ -v
```

Tests cover: auth (login, logout, invalid login), trial expiry downgrade, Stripe webhook (canceled, unpaid, incomplete_expired, deleted).
