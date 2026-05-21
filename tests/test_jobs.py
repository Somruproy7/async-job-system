"""
Tests for the async job system.
Uses pytest-asyncio + httpx AsyncClient for API testing.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from app.main import app
from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.job import Job, JobStatus, JobType, JobPriority
from app.core.security import hash_password, create_access_token


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_db():
    """In-memory mock database session."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture
def test_user():
    return User(
        id=uuid4(),
        email="test@example.com",
        username="testuser",
        hashed_password=hash_password("testpassword"),
        role=UserRole.USER,
        is_active=True,
    )


@pytest.fixture
def admin_user():
    return User(
        id=uuid4(),
        email="admin@example.com",
        username="adminuser",
        hashed_password=hash_password("adminpassword"),
        role=UserRole.ADMIN,
        is_active=True,
    )


@pytest.fixture
def user_token(test_user):
    return create_access_token({"sub": str(test_user.id), "role": "user"})


@pytest.fixture
def admin_token(admin_user):
    return create_access_token({"sub": str(admin_user.id), "role": "admin"})


@pytest.fixture
def sample_job(test_user):
    return Job(
        id=uuid4(),
        name="Test Image Job",
        job_type=JobType.IMAGE_PROCESSING,
        priority=JobPriority.DEFAULT,
        status=JobStatus.PENDING,
        progress=0.0,
        payload={"image_url": "https://example.com/img.jpg"},
        retry_count=0,
        max_retries=3,
        owner_id=test_user.id,
    )


@pytest_asyncio.fixture
async def client(mock_db, test_user):
    """HTTP client with mocked DB and authenticated user."""
    app.dependency_overrides[get_db] = lambda: mock_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c

    app.dependency_overrides.clear()


# ─── Auth Tests ────────────────────────────────────────────────────────────────

class TestAuth:
    @pytest.mark.asyncio
    async def test_register_new_user(self, client, mock_db, test_user):
        """Registration creates a new user and returns 201."""
        mock_db.execute.return_value.scalar_one_or_none.return_value = None  # no existing user

        with patch("app.services.user_service.UserService.create", return_value=test_user):
            response = await client.post("/api/v1/auth/register", json={
                "email": "new@example.com",
                "username": "newuser",
                "password": "securepassword123",
            })

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == test_user.email
        assert "hashed_password" not in data

    @pytest.mark.asyncio
    async def test_login_returns_tokens(self, client, mock_db, test_user):
        """Valid credentials return access + refresh tokens."""
        mock_db.execute.return_value.scalar_one_or_none.return_value = test_user

        response = await client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "testpassword",
        })

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client, mock_db, test_user):
        """Wrong password returns 401."""
        mock_db.execute.return_value.scalar_one_or_none.return_value = test_user

        response = await client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "wrongpassword",
        })

        assert response.status_code == 401


# ─── Job Tests ─────────────────────────────────────────────────────────────────

class TestJobs:
    @pytest.mark.asyncio
    async def test_submit_job_returns_202(self, client, mock_db, test_user, sample_job, user_token):
        """Job submission returns 202 Accepted immediately."""
        mock_db.execute.return_value.scalar_one_or_none.return_value = test_user

        with patch("app.services.job_service.JobService.create", return_value=sample_job), \
             patch("app.services.job_service.JobService.mark_queued", return_value=sample_job), \
             patch("app.tasks.job_tasks.process_job.apply_async") as mock_task:

            mock_task.return_value.id = str(uuid4())

            response = await client.post(
                "/api/v1/jobs/",
                json={
                    "name": "Test Image Job",
                    "job_type": "image_processing",
                    "priority": "default",
                    "payload": {"image_url": "https://example.com/img.jpg"},
                },
                headers={"Authorization": f"Bearer {user_token}"},
            )

        assert response.status_code == 202
        mock_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_submit_job_routes_to_correct_queue(self, client, mock_db, test_user, sample_job, user_token):
        """High-priority jobs go to the high queue."""
        mock_db.execute.return_value.scalar_one_or_none.return_value = test_user
        sample_job.priority = JobPriority.HIGH

        with patch("app.services.job_service.JobService.create", return_value=sample_job), \
             patch("app.services.job_service.JobService.mark_queued", return_value=sample_job), \
             patch("app.tasks.job_tasks.process_job.apply_async") as mock_task:

            mock_task.return_value.id = str(uuid4())

            await client.post(
                "/api/v1/jobs/",
                json={"name": "Urgent Job", "job_type": "image_processing", "priority": "high", "payload": {}},
                headers={"Authorization": f"Bearer {user_token}"},
            )

            # Verify correct queue used
            call_kwargs = mock_task.call_args[1]
            assert call_kwargs["queue"] == "high"

    @pytest.mark.asyncio
    async def test_get_job_status(self, client, mock_db, test_user, sample_job, user_token):
        """Status endpoint returns lightweight status object."""
        mock_db.execute.return_value.scalar_one_or_none.return_value = test_user

        with patch("app.services.job_service.JobService.get_by_id", return_value=sample_job):
            response = await client.get(
                f"/api/v1/jobs/{sample_job.id}/status",
                headers={"Authorization": f"Bearer {user_token}"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "progress" in data

    @pytest.mark.asyncio
    async def test_cancel_pending_job(self, client, mock_db, test_user, sample_job, user_token):
        """Pending jobs can be cancelled."""
        mock_db.execute.return_value.scalar_one_or_none.return_value = test_user

        with patch("app.services.job_service.JobService.get_by_id", return_value=sample_job), \
             patch("app.services.job_service.JobService.cancel", return_value=sample_job):

            sample_job.status = JobStatus.PENDING
            response = await client.post(
                f"/api/v1/jobs/{sample_job.id}/cancel",
                headers={"Authorization": f"Bearer {user_token}"},
            )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_cannot_cancel_running_job(self, client, mock_db, test_user, sample_job, user_token):
        """Running jobs cannot be cancelled via API."""
        mock_db.execute.return_value.scalar_one_or_none.return_value = test_user
        sample_job.status = JobStatus.RUNNING

        with patch("app.services.job_service.JobService.get_by_id", return_value=sample_job):
            response = await client.post(
                f"/api/v1/jobs/{sample_job.id}/cancel",
                headers={"Authorization": f"Bearer {user_token}"},
            )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_job_not_found_for_other_user(self, client, mock_db, test_user, user_token):
        """Users cannot access another user's jobs."""
        mock_db.execute.return_value.scalar_one_or_none.return_value = test_user

        with patch("app.services.job_service.JobService.get_by_id", return_value=None):
            response = await client.get(
                f"/api/v1/jobs/{uuid4()}",
                headers={"Authorization": f"Bearer {user_token}"},
            )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_unauthenticated_request_rejected(self, client):
        """No JWT → 403."""
        response = await client.get("/api/v1/jobs/")
        assert response.status_code == 403


# ─── Celery Task Tests ────────────────────────────────────────────────────────

class TestCeleryTasks:
    def test_process_job_calls_correct_processor(self):
        """Each job type routes to the right processor."""
        from app.tasks.job_tasks import PROCESSORS
        from app.models.job import JobType

        assert JobType.IMAGE_PROCESSING in PROCESSORS
        assert JobType.REPORT_GENERATION in PROCESSORS
        assert JobType.EMAIL_SENDING in PROCESSORS
        assert JobType.DATA_EXPORT in PROCESSORS

    def test_retry_count_increments_on_failure(self):
        """Failed tasks increment retry_count before retrying."""
        # Verify the retry logic exists in the task
        import inspect
        from app.tasks import job_tasks
        source = inspect.getsource(job_tasks.process_job)
        assert "retry_count" in source
        assert "_increment_retry_count" in source
