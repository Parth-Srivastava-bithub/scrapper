"""Tests for scraper-worker scheduler configuration."""

from scheduler import scheduler


def test_scheduler_jobs_configured():
    job_ids = [job.id for job in scheduler.get_jobs()]
    assert "runpod_catalog" in job_ids
    assert "novita_catalog" in job_ids
    assert "vast_catalog" in job_ids
    assert "runpod_datacenters" in job_ids
    assert "novita_datacenters" in job_ids
    assert "vast_datacenters" in job_ids
    assert "runpod_live" in job_ids
    assert "novita_live" in job_ids
    assert "vast_live" in job_ids
