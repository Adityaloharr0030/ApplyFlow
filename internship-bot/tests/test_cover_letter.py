from agent.cover_letter import generate_cover_letter
from core.models import UserProfile, JobListing
from unittest.mock import patch

@patch("agent.cover_letter.get_ai_response")
def test_generate_cover_letter(mock_get_ai_response):
    mock_get_ai_response.return_value = "This is a tailored cover letter."
    
    profile = UserProfile(name="Test", user_id=1)
    listing = JobListing(title="Engineer", company="Google")
    
    result = generate_cover_letter(profile, listing)
    
    assert result == "This is a tailored cover letter."
    mock_get_ai_response.assert_called_once()
