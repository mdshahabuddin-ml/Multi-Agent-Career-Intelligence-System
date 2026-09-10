"""Integration tests for Resume API endpoints."""

import pytest
from fastapi.testclient import TestClient
from io import BytesIO


class TestResumeAPI:
    """Tests for resume endpoints."""

    def test_upload_resume_success(self, client: TestClient, auth_headers):
        """Test successful resume upload."""
        file_content = b"John Doe\nSoftware Engineer\n\nEXPERIENCE\nSenior Engineer at TechCorp\n\nSKILLS\nPython, React, AWS"
        files = {"file": ("resume.txt", BytesIO(file_content), "text/plain")}
        data = {"is_primary": "false"}

        response = client.post(
            "/api/resume/upload",
            files=files,
            data=data,
            headers=auth_headers,
        )

        assert response.status_code == 201
        result = response.json()
        assert "id" in result
        assert result["filename"] == "resume.txt"
        assert result["status"] == "uploaded"

    def test_upload_resume_invalid_type(self, client: TestClient, auth_headers):
        """Test upload with invalid file type."""
        files = {"file": ("resume.exe", BytesIO(b"malicious"), "application/x-msdownload")}
        data = {"is_primary": "false"}

        response = client.post(
            "/api/resume/upload",
            files=files,
            data=data,
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "not allowed" in response.json()["detail"].lower()

    def test_upload_resume_too_large(self, client: TestClient, auth_headers):
        """Test upload with file too large."""
        large_content = b"x" * (11 * 1024 * 1024)  # 11MB > 10MB limit
        files = {"file": ("resume.txt", BytesIO(large_content), "text/plain")}
        data = {"is_primary": "false"}

        response = client.post(
            "/api/resume/upload",
            files=files,
            data=data,
            headers=auth_headers,
        )

        assert response.status_code == 413

    def test_parse_resume_success(self, client: TestClient, auth_headers, test_resume, db_session, tmp_path):
        """Test parsing uploaded resume."""
        real_file = tmp_path / "resume.txt"
        real_file.write_bytes((test_resume.raw_text or "John Doe").encode("utf-8"))
        test_resume.file_path = str(real_file)
        test_resume.mime_type = "text/plain"
        test_resume.original_filename = "resume.txt"
        test_resume.filename = "resume.txt"
        db_session.add(test_resume)
        db_session.commit()
        db_session.refresh(test_resume)
        response = client.post(
            f"/api/resume/{test_resume.id}/parse",
            headers=auth_headers,
        )

        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "parsed"
        assert "sections" in result
        assert "skills_count" in result
        assert result["skills_count"] >= 0

    def test_parse_nonexistent_resume(self, client: TestClient, auth_headers):
        """Test parsing nonexistent resume."""
        response = client.post(
            "/api/resume/99999/parse",
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_ats_analysis(self, client: TestClient, auth_headers, test_resume):
        """Test ATS analysis of resume."""
        response = client.post(
            f"/api/resume/{test_resume.id}/ats",
            data={"target_role": "software engineer"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        result = response.json()
        assert "overall_score" in result
        assert "breakdown" in result
        assert "recommendations" in result
        assert 0 <= result["overall_score"] <= 100

    def test_resume_review(self, client: TestClient, auth_headers, test_resume):
        """Test comprehensive resume review."""
        response = client.post(
            f"/api/resume/{test_resume.id}/review",
            headers=auth_headers,
        )

        assert response.status_code == 200
        result = response.json()
        assert "content" in result
        assert "experience" in result
        assert "skills" in result
        assert "projects" in result
        assert "overall" in result
        assert "word_count" in result

    def test_list_resumes(self, client: TestClient, auth_headers, test_resume):
        """Test listing user resumes."""
        response = client.get("/api/resume/", headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)
        assert len(result) >= 1
        assert result[0]["id"] == test_resume.id

    def test_get_resume(self, client: TestClient, auth_headers, test_resume):
        """Test getting specific resume."""
        response = client.get(f"/api/resume/{test_resume.id}", headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        assert result["id"] == test_resume.id
        assert result["original_filename"] == test_resume.original_filename

    def test_delete_resume(self, client: TestClient, auth_headers, test_resume, db_session):
        """Test deleting resume."""
        response = client.delete(f"/api/resume/{test_resume.id}", headers=auth_headers)

        assert response.status_code == 204

        # Verify it's deleted
        response = client.get(f"/api/resume/{test_resume.id}", headers=auth_headers)
        assert response.status_code == 404

    def test_set_primary_resume(self, client: TestClient, auth_headers, test_resume, test_user, db_session):
        """Test setting resume as primary."""
        from backend.models import Resume, ResumeStatus

        # Create another resume
        resume2 = Resume(
            user_id=test_user.id,
            filename="resume2.txt",
            original_filename="resume2.txt",
            file_path="/tmp/resume2.txt",
            file_size=100,
            mime_type="text/plain",
            status=ResumeStatus.PARSED,
            is_primary=False,
        )
        db_session.add(resume2)
        db_session.commit()
        db_session.refresh(resume2)

        response = client.post(f"/api/resume/{resume2.id}/primary", headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        assert result["is_primary"] is True

        # Verify old primary is no longer primary
        response = client.get(f"/api/resume/{test_resume.id}", headers=auth_headers)
        assert response.json()["is_primary"] is False

    def test_unauthorized_access(self, client: TestClient, test_resume, second_user, db_session):
        """Test that users can't access other users' resumes."""
        # Login as second user
        from backend.utils.security import create_access_token
        token = create_access_token(data={"sub": second_user.id})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get(f"/api/resume/{test_resume.id}", headers=headers)
        assert response.status_code == 404  # Not found for this user


class TestResumeSecurity:
    """Security tests for resume endpoints."""

    def test_file_type_validation(self, client: TestClient, auth_headers):
        """Test that only allowed file types are accepted."""
        # Try uploading a PDF with wrong extension
        files = {"file": ("resume.pdf", BytesIO(b"%PDF-1.4"), "application/pdf")}
        response = client.post("/api/resume/upload", files=files, headers=auth_headers)
        # Should work for PDF
        assert response.status_code == 201

    def test_filename_sanitization(self, client: TestClient, auth_headers):
        """Test that malicious filenames are rejected (intentional 400 validation)."""
        malicious_filename = "../../../etc/passwd"
        files = {"file": (malicious_filename, BytesIO(b"content"), "text/plain")}
        response = client.post("/api/resume/upload", files=files, headers=auth_headers)
        assert response.status_code == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v"])