# Job System Dashboard

A modern web dashboard for managing and monitoring async jobs.

## 🚀 Quick Start

The dashboard is automatically started with Docker Compose:

```bash
docker compose up -d
```

Then open your browser to: **http://localhost:3001**

## 👥 User Accounts

### Test User (Already Created)
- **Email**: test@example.com
- **Password**: testpass123
- **Role**: User (can only see their own jobs)

### Create Admin Account
To create an admin account, you need to manually update the database:

```bash
# Connect to PostgreSQL
docker compose exec postgres psql -U jobuser jobsdb

# Update user role to admin
UPDATE users SET role = 'admin' WHERE email = 'test@example.com';
\q
```

Or register a new account and then promote it to admin.

## ✨ Features

### For All Users
- ✅ Login / Register
- ✅ View your jobs
- ✅ Create new jobs
- ✅ View job details (status, progress, results)
- ✅ Cancel pending/queued jobs
- ✅ Retry failed jobs
- ✅ Real-time job status updates (auto-refresh every 5 seconds)
- ✅ Dashboard statistics

### For Admins
- ✅ View ALL jobs from all users
- ✅ Same management capabilities as users

## 📊 Dashboard Sections

### Stats Cards
- **Total Jobs**: All jobs in the system
- **Completed**: Successfully finished jobs
- **Running**: Currently executing jobs
- **Failed**: Jobs that encountered errors

### Jobs Table
Shows all jobs with:
- Job name and type
- Current status with color-coded badges
- Progress bar (0-100%)
- Priority level
- Creation timestamp
- Action buttons (View, Cancel, Retry)

### Create Job Modal
Submit new jobs with:
- Job name
- Job type (Image Processing, Report Generation, Email Sending, Data Export)
- Priority (High, Default, Low)
- Custom JSON payload

### Job Details Modal
View complete job information:
- Job ID and metadata
- Status and progress
- Timestamps (created, started, completed)
- Duration and queue wait time
- Retry count
- Payload and result data
- Error details (if failed)

## 🎨 Job Types

### 1. Image Processing
Process and transform images
```json
{
  "image_url": "https://example.com/image.jpg",
  "width": 800,
  "format": "webp"
}
```

### 2. Report Generation
Generate PDF/Excel reports
```json
{
  "report_type": "sales",
  "date_range": "2024-01-01 to 2024-12-31",
  "filters": {}
}
```

### 3. Email Sending
Send bulk emails
```json
{
  "recipients": ["user1@example.com", "user2@example.com"],
  "template_id": "welcome",
  "subject": "Welcome!"
}
```

### 4. Data Export
Export data to various formats
```json
{
  "query": "SELECT * FROM users",
  "format": "csv",
  "destination": "s3://bucket/export.csv"
}
```

## 🔧 Configuration

### API Endpoint
The dashboard connects to the API at `http://localhost:8000/api/v1`

To change this, edit `frontend/app.js`:
```javascript
const API_BASE_URL = 'http://your-api-url/api/v1';
```

### Port
The dashboard runs on port 3001 by default. To change it, edit `docker-compose.yml`:
```yaml
frontend:
  ports:
    - "YOUR_PORT:80"
```

And update CORS in `.env`:
```
ALLOWED_ORIGINS=["http://localhost:YOUR_PORT"]
```

## 🔐 Security

- JWT-based authentication
- Access tokens expire after 30 minutes
- Refresh tokens for seamless re-authentication
- Users can only see their own jobs
- Admins can see all jobs
- Passwords are hashed with bcrypt

## 🎯 Usage Tips

1. **Auto-Refresh**: The dashboard automatically refreshes job data every 5 seconds
2. **Progress Tracking**: Watch jobs progress in real-time with the progress bar
3. **Quick Actions**: Use the action buttons to quickly cancel or retry jobs
4. **Detailed View**: Click "View" to see complete job information including payloads and results
5. **Job Templates**: When creating a job, the payload field auto-fills with a template based on job type

## 🐛 Troubleshooting

### Can't connect to API
- Ensure the API container is running: `docker ps | grep jobsystem_api`
- Check API logs: `docker logs jobsystem_api`
- Verify CORS settings in `.env` include your frontend URL

### Jobs not updating
- Check browser console for errors (F12)
- Verify you're logged in (token not expired)
- Refresh the page manually

### Can't create jobs
- Ensure your JSON payload is valid
- Check that you're logged in
- Verify the API is accessible

## 📱 Mobile Responsive

The dashboard is fully responsive and works on:
- Desktop browsers
- Tablets
- Mobile phones

## 🎨 Customization

### Colors
Edit `frontend/styles.css` to change the color scheme:
```css
:root {
    --primary: #4f46e5;  /* Main brand color */
    --success: #10b981;  /* Success states */
    --danger: #ef4444;   /* Error states */
    /* ... more colors */
}
```

### Branding
Update the title and logo in `frontend/index.html`

## 📄 License

Part of the Async Job Processing System
