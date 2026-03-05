# Railway Deployment

## Required: Persistent Volume for SQLite

The app uses **SQLite** for games/odds data (collect, model). Without a persistent volume, this data is lost on every deploy.

### Setup

1. In Railway dashboard: **Create a Volume** and attach it to your web service.
2. Set the **mount path** to `/data`.
3. Railway will auto-set `RAILWAY_VOLUME_MOUNT_PATH=/data` at runtime.
4. SQLite will write to `/data/sharp_picks.db`.

### If data still doesn't persist

- **Check volume is attached**: In Railway → your service → Volumes. You should see a volume with mount path `/data`.
- **Permissions**: If the app runs as non-root, add `RAILWAY_RUN_UID=0` to service variables.
- **Verify**: After deploy, check Admin → Health Checks. The `sqlite` check shows path, `persistent`, and `games` count.

### Database overview

- **PostgreSQL** (DATABASE_URL): Users, Picks, Passes, ModelRuns — managed by Railway.
- **SQLite** (via volume): Games, odds — requires the `/data` volume.

### Push notifications (FCM)

Set **FIREBASE_SERVICE_ACCOUNT_JSON** to the full JSON from your Firebase service account (Project Settings → Service accounts → Generate new private key). Paste the entire JSON as the env value.

Alternatively, add `firebase-service-account.json` to the project root (ensure it's not in .gitignore for deploy, or use a build secret).

For **iOS** push, upload your APNs key in Firebase Console → Project Settings → Cloud Messaging → Apple app configuration.
