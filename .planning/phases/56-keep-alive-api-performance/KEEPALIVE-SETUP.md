# Keep-Alive Setup: UptimeRobot

## Why
Render free tier sleeps after 15 min of inactivity. External pinger prevents this.

## Setup Steps

1. Go to https://uptimerobot.com and create a free account
2. Click "Add New Monitor"
3. Configure:
   - Monitor Type: **HTTP(s)**
   - Friendly Name: `Holo Backend`
   - URL: `https://<your-render-app>.onrender.com/`
   - Monitoring Interval: **5 minutes** (free tier minimum)
4. Click "Create Monitor"

## What Gets Pinged
- `GET /` returns `{"status": "ok", "service": "holo"}` — zero DB access, instant response
- This is already implemented in `backend/app/main.py` (root endpoint)

## Alternative: cron-job.org
1. Go to https://cron-job.org and create a free account
2. Create a new cron job
3. URL: `https://<your-render-app>.onrender.com/`
4. Schedule: Every 5 minutes
5. HTTP Method: GET

## Notes
- Free tier gives 50 monitors — we only need 1
- Ping interval of 5 min is sufficient (Render sleeps after 15 min)
- Consider market-hours-only pinging (Mon-Fri 8:00-16:00 ICT) to conserve budget
- No code changes needed — this is purely external configuration
