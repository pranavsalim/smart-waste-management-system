# Cloud-Based Smart Waste Management System

A student mini-project built with Flask, SQLite, HTML, CSS and JavaScript. It supports citizen registration/login, garbage complaint submission with an optional photo, ticket IDs, complaint tracking, and an admin dashboard.

## 1. Requirements
- Python 3.10 or newer
- Git
- Visual Studio Code (recommended)

## 2. Run locally (Windows PowerShell)
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python app.py
```
Open http://127.0.0.1:5000

If PowerShell blocks activation, run:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## 3. Run locally (macOS/Linux)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

## 4. Demo admin account
- Email: `admin@smartwaste.local`
- Password: `Admin@123`

Change these values before any deployment. For local demo, set `ADMIN_EMAIL` and `ADMIN_PASSWORD` environment variables before the first run. The initial admin is created only if that email does not already exist.

## 5. Test
```bash
pytest
```

## 6. GitHub
Create an empty GitHub repository, then:
```bash
git init
git add .
git commit -m "Initial Smart Waste Management application"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/smart-waste-management.git
git push -u origin main
```

## 7. Important deployment note
This starter is a local development version. It stores data in SQLite and uploaded images on the local filesystem. Those are suitable for learning and a local demo, but are not durable/shared storage for most cloud deployments. Before public cloud deployment, move the database to a managed database (for example DynamoDB or RDS), move images to object storage (for example S3), set a strong secret in the hosting platform, disable debug mode, add CSRF protection/rate limiting, and configure HTTPS. Never commit `.env`, passwords, database files or private keys.

## 8. Main routes
- `/` — landing page
- `/register` — citizen registration
- `/login` — login
- `/dashboard` — citizen's complaints
- `/complaints/new` — submit complaint
- `/admin` — admin dashboard
- `/api/health` — health check JSON
- `/api/complaints` — authenticated user's complaint JSON
AWS EC2 Deployment and GitHub Actions CI/CD is successfully configured.
