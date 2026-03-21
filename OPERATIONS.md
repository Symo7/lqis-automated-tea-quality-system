# LQIS Operations Guide

This guide outlines the essential procedures for maintaining, rolling out, and recovering the LQIS (Automated Tea Quality) system.

---

## 🚀 Deployment & Rollout

LQIS uses **Render** for zero-downtime deployments. Every push to the `main` branch triggers an automatic build.

### Pre-Rollout Checklist
1. **Smoke Test**: Run the local smoke test before pushing:
   ```bash
   .venv\Scripts\python.exe smoke_test.py
   ```
2. **Database Migrations**: Render runs `python manage.py migrate` automatically during the build phase. Ensure your migrations are committed.
3. **Environment Flags**: Check if `DEMO_MODE_ENABLED` or `SENTRY_DSN` need updates in the Render Dashboard.

### Post-Rollout Smoke Test
After the green "Live" status appears in Render, run the smoke test again against the production URL:
```bash
# Ensure SMOKE_TEST_URL is set or matches script default
.venv\Scripts\python.exe smoke_test.py
```

---

## 🛠 Database Continuity (Backups & Restores)

While Render provides automated database management, manual hourly or daily backups are recommended for high-risk updates.

### Manual Backup (Local or Production Shell)
Exports a timestamped JSON snapshot of all core data to the `backups/` directory:
```bash
python manage.py backup_data
```

### Restoration (Local or Production Shell)
**⚠️ WARNING: Destructive operation.** Overwrites existing data with the content of the backup file.
```bash
python manage.py restore_data backups/lqis_backup_20260322_000000.json
```

---

## 🆘 Rollback Strategy

If a deployment causes an issue (discovered by Sentry or Smoke Tests), you can roll back in under 60 seconds.

### 1. Revert Git Commit
Revert the last commit on your local `main` branch and push:
```bash
git revert HEAD
git push origin main
```
Render will instantly build and deploy the previous stable version.

### 2. Manual Rollback in Render
1. Go to the **Events** or **Deploys** tab in Render.
2. Find the last successful "Deploy live" entry.
3. Click the "..." button and select **"Roll back to this deploy"**.
4. Render will instantly point traffic back to the previous stable build.

---

## 📊 Monitoring & Alerts

- **Errors**: Check [sentry.io](https://sentry.io) for real-time exceptions.
- **Performance**: Monitor the Sentry "Performance" tab for slow SQL queries or N+1 patterns.
- **Logs**: Use `render logs -s web` (via Render CLI) or the dashboard log viewer for live request monitoring.
