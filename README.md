# Kairo Co Backend (FastAPI)

Backend API for the Kairo Co property submission and testimonial system.
Handles property form submissions, sequential Property IDs, Google Drive
photo storage, Google Sheets record-keeping, email notifications, and a
moderated testimonial feed.

## Project Structure

```
app/
  main.py                 FastAPI app, CORS, startup checks
  config.py               Settings loaded from .env (pydantic-settings)
  models/
    property.py           Property submission request/response models
    testimonial.py         Testimonial request/response models
  routers/
    properties.py         POST /api/properties/submit
    testimonials.py        POST /api/testimonials/submit, GET /api/testimonials
  services/
    google_auth.py         Shared Google service-account auth
    sheets_service.py       Sheets read/append/ID-generation
    drive_service.py        Drive folder creation + image upload
    email_service.py        Gmail SMTP notifications
  utils/
    id_generator.py         Sequential ID formatting + concurrency locks
    validators.py            Image type/size validation
deploy/
  kairoco-backend.service   systemd unit example
  nginx.conf.example        nginx reverse proxy example
requirements.txt
.env.example
```

## 1. Google Cloud Setup

1. Create a Google Cloud project → enable **Google Sheets API** and **Google Drive API**.
2. Create a **Service Account** → generate a JSON key → save it as `service_account.json` in the project root.
3. Create two Google Sheets: "Properties" and "Testimonials" (tab names must match `PROPERTIES_SHEET_NAME` / `TESTIMONIALS_SHEET_NAME` in `.env`).
4. Create a Drive folder named e.g. "Property Photos" — this is the parent folder that per-property subfolders will be created inside.
5. Share **both Sheets** and the **Drive folder** with the service account's email (found inside `service_account.json`, looks like `xxx@xxx.iam.gserviceaccount.com`) with **Editor** access.
6. Copy the Sheet IDs (from each URL: `.../d/<ID>/edit`) and the Drive folder ID (from its URL) into `.env`.

## 2. Gmail Setup

1. Enable 2-Step Verification on the Gmail account used for sending.
2. Generate an **App Password** (Google Account → Security → App Passwords).
3. Put the Gmail address and app password into `.env`.

## 3. Local Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edit .env with real values, and place service_account.json in the project root

uvicorn app.main:app --reload
```

API docs available at `http://localhost:8000/docs`.

## 4. Endpoints

| Method | Path                        | Purpose                                      |
|--------|-----------------------------|-----------------------------------------------|
| POST   | `/api/properties/submit`    | Submit a property (multipart/form-data + images) |
| POST   | `/api/testimonials/submit`  | Submit a testimonial (JSON, status = Pending) |
| GET    | `/api/testimonials`         | Public list of **Approved** testimonials only |
| GET    | `/api/health`                | Health check                                  |

### Property submission fields (`multipart/form-data`)
`full_name, email, phone, property_address, bedrooms, guests, features, smoking_allowed (Yes/No), pets_allowed (Yes/No), images[]`

Response: `{ "property_id": "KC-00047", "status": "Pending", "drive_folder_link": "..." }`

## 5. How the Moderation Workflows Work

- **Property status**: Kairo Co staff edit the `Status` column directly in the Properties sheet (Pending → Under Review → Approved/Rejected). This is a manual, spreadsheet-only workflow — no separate admin UI exists yet (see "Future Enhancements" in the client presentation).
- **Testimonials**: `GET /api/testimonials` re-reads the Testimonials sheet on every request and returns only rows where `Status == "Approved"`. Flipping a row's status in Google Sheets takes effect the next time the frontend fetches the list — no redeploy, cache-clear, or webhook required.

## 6. Security Notes

- All secrets (Google service account path, Gmail credentials, sheet/folder IDs) live in `.env` — never in code, never sent to the frontend.
- `.env` and `service_account.json` are both git-ignored.
- CORS is restricted to the origins listed in `FRONTEND_ORIGINS` — update this to your real domain(s) before going live.
- The sequential-ID lock (`utils/id_generator.py`) is process-local. This is fine for a single-instance deployment (the default here); if you ever scale to multiple backend processes/machines behind a load balancer, replace it with an atomic counter (e.g. a database sequence) to avoid duplicate IDs.

## 7. Deployment (Hostinger VPS or any Python-supported server)

```bash
# on the server
git clone <your-repo> /var/www/kairoco-backend
cd /var/www/kairoco-backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # fill in real values
# upload service_account.json alongside it

sudo cp deploy/kairoco-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now kairoco-backend

sudo cp deploy/nginx.conf.example /etc/nginx/sites-available/kairoco-backend
sudo ln -s /etc/nginx/sites-available/kairoco-backend /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx   # HTTPS
```

The app works identically locally (`uvicorn`) and in production (`gunicorn` +
`uvicorn` workers behind `nginx`) — no code changes needed between environments,
only `.env` values.
