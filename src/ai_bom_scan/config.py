"""
Configuration module for ai-bom-scan
"""

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()


@dataclass
class Config:
    """Configuration class for the ai-bom-scan CLI"""
    
    api_token: Optional[str] = None
    org_id: Optional[str] = None
    group_id: Optional[str] = None
    api_url: str = "https://api.snyk.io"
    api_version: str = "2025-07-22"
    debug: bool = False
    
    def __post_init__(self) -> None:
        """Post-initialization to handle environment variable fallbacks"""
        # Use environment variables as fallbacks
        if not self.api_token:
            self.api_token = os.getenv("SNYK_TOKEN")
            
        if not self.org_id:
            self.org_id = os.getenv("SNYK_ORG_ID")
            
        if not self.group_id:
            self.group_id = os.getenv("SNYK_GROUP_ID")
            
        if not self.api_url:
            self.api_url = os.getenv("SNYK_API_URL", "https://api.snyk.io")
    
    @property
    def base_api_url(self) -> str:
        """Get the base API URL with rest prefix"""
        return f"{self.api_url.rstrip('/')}/rest"
    
    @property
    def headers(self) -> dict:
        """Get the standard headers for API requests"""
        return {
            "Authorization": f"token {self.api_token}",
            "Content-Type": "application/vnd.api+json",
            "Accept": "application/vnd.api+json",
        }
    
    def validate(self) -> None:
        """Validate that required configuration is present"""
        if not self.api_token:
            raise ValueError("API token is required. Set SNYK_TOKEN environment variable.")
            
        if not self.org_id and not self.group_id:
            raise ValueError("Organization ID or Group ID is required. Set SNYK_ORG_ID or SNYK_GROUP_ID environment variable.")
    
    def get_aibom_url(self) -> str:
        """Get the AI-BOM creation endpoint URL"""
        return f"{self.base_api_url}/orgs/{self.org_id}/ai_boms"
    
    def get_aibom_job_url(self, job_id: str) -> str:
        """Get the AI-BOM job status endpoint URL"""
        return f"{self.base_api_url}/orgs/{self.org_id}/ai_bom_jobs/{job_id}"
    
    def get_aibom_result_url(self, aibom_id: str) -> str:
        """Get the AI-BOM result endpoint URL"""
        return f"{self.base_api_url}/orgs/{self.org_id}/ai_boms/{aibom_id}"
