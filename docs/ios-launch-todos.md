# iOS launch TODOs

The action items that need to ship the moment App Store Review approves the
SharpPicks: Signals iOS app and the listing goes live.

Until that happens, all of the marketing/email surfaces below are
intentionally Google-only with "iOS Coming Soon" labels, and several admin
metrics are gated off so sandbox/TestFlight noise doesn't pollute the
dashboard.

---

## 1. Get the App Store URL

Capacitor `appId` is `com.sharppicksllc.signals` (per `capacitor.config.json`).
Once the listing is live, the canonical URL pattern is:

```
https://apps.apple.com/us/app/sharppicks-signals/id<NUMERIC_ID>
```

Find `<NUMERIC_ID>` on App Store Connect → My Apps → SharpPicks: Signals →
App Information → Apple ID. Save it as a constant — every link below uses
the same URL.

---

## 2. Railway env var (5 seconds — start with this)

Set in Railway → SharpPicks service → Variables:

```
IOS_PROD_LIVE=1
```

This unlocks `services/sources/revenuecat.py`. Without it the RC source
returns all zeros with a "iOS not yet live" note. With it set, the source
starts counting real iOS subs, MRR, conversions, billing issues — see the
admin Command tab → Trial Pipeline for the new fields.

---

## 2A. APNs Authentication Key in Firebase Console (LAUNCH BLOCKER)

Diagnosed 2026-05-04 via `/api/admin/firebase-diagnose`: Android FCM
sends work (200 OK), iOS FCM sends fail with 401. Service-account auth
is fine — the gap is between Firebase and Apple Push Notification
Service.

**Without this fixed, every iOS user gets zero push notifications**
(no pick alerts, no pass-day notifications, no results, no weekly
summaries). TestFlight users + Build 6 installers + every future
App Store user are silently broken.

**Fix steps (~10 min if you have Apple Dev access):**

1. **Apple Developer Portal** → Certificates, Identifiers & Profiles →
   **Keys** → **+** → name it `SharpPicks FCM` → check
   `Apple Push Notifications service (APNs)` → Continue → Register →
   download the `.p8` (one-time download, save it).
2. Note three values from the new key page:
   - **Key ID** (10 chars at the top)
   - **Team ID** (top right of any Apple Developer page; current value:
     `GM86B8Y7D7` per `ios/App/SharpPicks.storekit`)
   - Bundle ID: `com.sharppicksllc.signals`
3. **Firebase Console** → sharp-picks project → Project Settings (gear) →
   **Cloud Messaging** tab → scroll to **Apple app configuration**.
4. Either click the existing entry for `com.sharppicksllc.signals` or
   add it (+ button).
5. **APNs Authentication Key** row → **Upload** the `.p8`, paste Key ID
   and Team ID, **Save**.

**Verify:**

```bash
curl -s -H "X-Cron-Secret: <secret>" \
  "https://app.sharppicks.ai/api/admin/firebase-diagnose" | jq '.real_token_probes.ios'
```

Should be `http_status: 200` (or 404/410 if the specific user reinstalled).
Anything other than 401 means the auth path is fixed.

---

## 3. Marketing site (`landing/`)

The customer-facing marketing site is in `landing/`, served at sharppicks.ai
(separate from `app.sharppicks.ai` which is the Flask + React WebView).

### `landing/index.html`

**Two App Store badges to enable** (hero + footer CTA):
- Lines around **315** (hero) and **562** (footer CTA strip)
- Each is structured as:
  ```html
  <a class="badge-link" href="#">
    <div class="store-badge dim">
      <svg ... App Store glyph ... />
      <div class="store-badge-text">
        <span class="store-badge-sm">Download on the</span>
        <span class="store-badge-lg">App Store</span>
      </div>
    </div>
    <span class="coming-label">Coming Soon</span>
  </a>
  ```

**Per badge, three edits:**
1. Replace `href="#"` with the App Store URL from §1
2. Remove the `dim` class from `<div class="store-badge dim">`
3. Delete the entire `<span class="coming-label">Coming Soon</span>` line

The Google Play badge above each App Store badge is already linked (lines
304 and 551) — leave it alone.

### `landing-site/index.html` (older copy)

Line **234** has `<span class="pill soon">WNBA — Coming Soon</span>` — that's
WNBA-related, NOT iOS. Leave it. Verify via diff against `landing/index.html`
whether `landing-site/` is still a deployed surface; if it's just a backup it
may not need updating at all.

---

## 4. Email templates (`templates/emails/`)

Currently every transactional + recurring email uses the shared header/footer
partial `templates/emails/wordmark.html` which contains a Google-Play-only
badge:

```html
<a href="https://play.google.com/store/apps/details?id=com.sharppicksllc.app" ...>
  <img src="https://play.google.com/intl/en_us/badges/static/images/badges/en_badge_web_generic.png"
       alt="Get it on Google Play" style="height:40px;border:0;" height="40">
</a>
```

(Line ~57-58 of `wordmark.html`.)

**Add the App Store badge alongside it** (see Apple's marketing badge guidelines
for the official asset URL — the standard is the black "Download on the App Store"
badge from <https://developer.apple.com/app-store/marketing/guidelines/>):

```html
<!-- existing Google badge -->
<a href="https://play.google.com/store/apps/details?id=com.sharppicksllc.app" style="text-decoration:none;margin-right:8px;" target="_blank">
  <img src="https://play.google.com/intl/en_us/badges/static/images/badges/en_badge_web_generic.png" alt="Get it on Google Play" style="height:40px;border:0;" height="40">
</a>
<!-- NEW App Store badge -->
<a href="https://apps.apple.com/us/app/sharppicks-signals/id<NUMERIC_ID>" style="text-decoration:none;" target="_blank">
  <img src="https://tools.applemediaservices.com/api/badges/download-on-the-app-store/black/en-us" alt="Download on the App Store" style="height:40px;border:0;" height="40">
</a>
```

**Emails that pull in `wordmark.html` (and therefore inherit the change automatically):**
- `templates/emails/signal.html` (daily signal alerts)
- `templates/emails/no_signal.html` (pass-day notifications)
- `templates/emails/grading.html` (pick result emails)
- `templates/emails/weekly_recap.html` (weekly summary)
- `templates/emails/welcome.html` (signup confirmation)

If any of those emails inline the badge directly instead of using the partial,
update them too — quick check:
```bash
grep -l "play.google" templates/emails/*.html
```

---

## 5. In-app surfaces (`templates/app-landing.html`, React `LandingPage.jsx`)

Both currently have iOS-aware code paths that fire when `Capacitor.getPlatform() === 'ios'`:

- `templates/app-landing.html` line ~206: `relabelForIOS()` rewrites trial CTAs
  to "Create Free Account" so the copy matches the iOS free-only signup flow.
  After App Review approval, this can stay as-is — iOS users still hit the
  free-account flow because IAP handles paid via the upgrade screen.

- `src/components/sharp/LandingPage.jsx` line 9: `isIOS` detection used
  throughout to render iOS-appropriate buttons.

Neither needs changes for launch, but verify after going live that the
in-app subscribe button still routes to `UpgradeScreen` → RevenueCat IAP
(not Stripe checkout — see `services/sources/stripe_metrics.py` audit notes).

---

## 6. iOS-specific exclusions in admin metrics

Already in place, but worth verifying after IOS_PROD_LIVE=1 is set:

| File | What it does |
|---|---|
| `services/sources/revenuecat.py` | Forces zeros until IOS_PROD_LIVE=1; once live, excludes is_internal + comped + deleted_at users from counts |
| `services/sources/stripe_metrics.py` | Excludes is_internal + comped + deleted_at customers from MRR + active_subs |
| `services/users_metrics.py` | _user_tags renders `[ios]` overlay when `pro_source='revenuecat'` |
| `services/headline.py` | Headline rules already combine Stripe + RC MRR — will start including real RC numbers automatically |

---

## 7. App Store Connect operational tasks

- Confirm subscription products (`pro_monthly`, `pro_yearly`) are in
  "Approved" status in App Store Connect → Subscriptions.
- Verify the RevenueCat dashboard offering (`default`) maps to those exact
  product IDs.
- Sandbox tester accounts can stay in App Store Connect → Users and Access →
  Sandbox; they won't pollute production metrics because all sandbox webhooks
  fire from a different environment that RevenueCat tags differently — but
  ProcessedEvent doesn't store that flag (see §2 reasoning), so the
  IOS_PROD_LIVE gate stays the safest backstop.

---

## 8. Post-launch verification checklist

After flipping IOS_PROD_LIVE=1 and updating the marketing/email links:

- [ ] `curl /api/admin/metrics` — `revenuecat.payload.ios_prod_live === true`,
      counts reflect actual sandbox-tester or real-customer activity
- [ ] Reload admin Command tab — Trial Pipeline shows iOS subs separately
- [ ] Send yourself a test email (welcome / weekly recap) — verify both
      Google Play AND App Store badges render
- [ ] Open sharppicks.ai on a phone — verify both store badges link out
      correctly, no "Coming Soon" label
- [ ] Tap the App Store badge from sharppicks.ai → opens App Store app to
      the SharpPicks: Signals listing
