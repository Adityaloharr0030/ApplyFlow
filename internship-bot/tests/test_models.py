from core.models import JobListing, UserProfile

def test_job_listing_score_clamp():
    # Should clamp score between 0 and 10
    j1 = JobListing(title="Engineer", score=-5)
    assert j1.score == 0
    
    j2 = JobListing(title="Engineer", score=15)
    assert j2.score == 10
    
    j3 = JobListing(title="Engineer", score=7)
    assert j3.score == 7

def test_candidate_profile_name():
    p = UserProfile(name="Test Candidate", user_id=1)
    assert p.name == "Test Candidate"
