# 📊 Dashboard Quick Start Guide

## 🌐 Access the Dashboard

Open your browser and go to: **http://localhost:3001**

## 🔑 Login Credentials

### Existing Test User
- **Email**: `test@example.com`
- **Password**: `testpass123`
- **Role**: Regular User

### Create New Account
1. Click "Register" on the login page
2. Fill in your email, username, and password
3. Click "Register"
4. Login with your new credentials

## 👑 Make Yourself Admin

To see ALL jobs (not just yours), promote your account to admin:

```bash
# Connect to database
docker compose exec postgres psql -U jobuser jobsdb

# Promote user to admin (replace email with yours)
UPDATE users SET role = 'admin' WHERE email = 'test@example.com';

# Exit
\q
```

Then logout and login again to see the changes.

## 📋 Dashboard Features

### 1. **Stats Overview**
At the top, you'll see 4 cards showing:
- 📋 Total Jobs
- ✅ Completed Jobs
- ⏳ Running Jobs
- ❌ Failed Jobs

### 2. **Create New Job**
Click the **"+ Create New Job"** button:

1. Enter a job name (e.g., "Process user avatar")
2. Select job type:
   - **Image Processing** - Resize/convert images
   - **Report Generation** - Create PDF/Excel reports
   - **Email Sending** - Send bulk emails
   - **Data Export** - Export data to CSV/JSON
3. Choose priority (High, Default, Low)
4. Edit the JSON payload (auto-filled with template)
5. Click **"Create Job"**

### 3. **View Jobs Table**
The table shows all your jobs with:
- **Status badges** (color-coded)
- **Progress bars** (0-100%)
- **Priority badges**
- **Action buttons**

### 4. **Job Actions**

#### View Details
Click **"View"** to see:
- Complete job information
- Payload data
- Results (when completed)
- Error messages (if failed)
- Execution timeline

#### Cancel Job
Click **"Cancel"** on pending/queued jobs to stop them before they start

#### Retry Job
Click **"Retry"** on failed jobs to run them again

### 5. **Auto-Refresh**
The dashboard automatically updates every 5 seconds - watch your jobs progress in real-time!

## 🎯 Example: Create an Image Processing Job

1. Click **"+ Create New Job"**
2. Name: `Resize product image`
3. Type: `Image Processing`
4. Priority: `High`
5. Payload:
```json
{
  "image_url": "https://example.com/product.jpg",
  "width": 800,
  "format": "webp"
}
```
6. Click **"Create Job"**
7. Watch it progress: Queued → Running → Success!

## 🔄 Job Status Meanings

| Status | Meaning |
|--------|---------|
| **Pending** | Job created, waiting to be queued |
| **Queued** | Job in queue, waiting for worker |
| **Running** | Worker is processing the job |
| **Success** | Job completed successfully ✅ |
| **Failed** | Job encountered an error ❌ |
| **Retrying** | Job failed, attempting retry |
| **Cancelled** | Job was cancelled by user |

## 🎨 Priority Levels

- **High** 🔴 - Processed first
- **Default** 🔵 - Normal processing
- **Low** ⚪ - Processed last

## 💡 Tips

1. **Keep the dashboard open** to watch jobs progress in real-time
2. **Use High priority** for urgent jobs
3. **Check job details** if a job fails to see the error
4. **Retry failed jobs** after fixing the issue
5. **Cancel jobs** if you submitted them by mistake

## 🚀 What's Next?

- Monitor your jobs in real-time
- Check the **Flower dashboard** at http://localhost:5555/flower/ (admin/flowerpass) for worker stats
- View **API docs** at http://localhost:8000/api/docs
- Create jobs via API for automation

## 🆘 Need Help?

- **Can't login?** Check if API is running: `docker ps | grep jobsystem_api`
- **Jobs not showing?** Click the 🔄 Refresh button
- **Can't create jobs?** Verify your JSON payload is valid
- **Want to see all jobs?** Promote yourself to admin (see above)

---

**Enjoy your Job System Dashboard! 🎉**
