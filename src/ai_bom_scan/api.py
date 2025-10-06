import logging
from typing import Optional
import requests
import time
import sys
from rich.console import Console

from .config import Config

console = Console()

class SnykAIBomAPIClient:
    """Snyk AI-BOM scanner client."""
    
    def __init__(self, config: Config):
        self.api_url = config.api_url
        self.org_id = config.org_id
        self.group_id = config.group_id
        self.api_version = config.api_version
        self.headers = {
            'Content-Type': 'application/vnd.api+json',
            'Authorization': f'token {config.api_token}'
        }
    
    def get_all_targets(self):
        """
        Fetches all targets from a list of Snyk organizations, handling pagination.
        """
        orgs = []
        if self.group_id:
            orgs = self.get_all_orgs_from_group()
        else:
            orgs.append({'id': self.org_id})

        targets = []
        for org in orgs:
            targets.extend(self.get_all_targets_from_org(org))
        
        return targets

    def get_all_orgs_from_group(self):
        """
        Fetches all organizations from a Snyk group, handling pagination.
        """
        orgs = []
        url = f"{self.api_url}/rest/groups/{self.group_id}/orgs?version={self.api_version}&limit=100"
        while url:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            orgs.extend(data.get('data', []))
            url = data.get('links', {}).get('next')
        return orgs
        
    def get_all_targets_from_org(self, org: Optional[dict]):
        """
        Fetches all targets from a Snyk organization, handling pagination.
        """

        if org:
            org_id = org.get('id')
        else:
            org_id = self.org_id

        targets = []
        # Start with the first page URL, limiting to 100 results per page
        url = f"{self.api_url}/rest/orgs/{org_id}/targets?version={self.api_version}&limit=100"
        
        # Loop as long as there is a "next" page URL
        while url:
            try:
                response = requests.get(url, headers=self.headers)
                response.raise_for_status() # Exit if there's an error
                data = response.json()
                
                # Add the targets from the current page to our list
                targets.extend(data.get('data', []))
                
                # Get the URL for the next page. If it doesn't exist, the loop will end.
                next_link = data.get('links', {}).get('next')
                if next_link:
                    url = f"{self.api_url}{next_link}" # The link is relative, so add the base URL
                else:
                    url = None # End the loop

            except requests.exceptions.RequestException as e:
                print(f"Error fetching targets: {e}", file=sys.stderr)
                return None
        
        return targets

    def process_target(self, target):
        """
        Generates and searches an AI-BOM for a single target.
        
        Returns:
            list: List of matched search terms, or empty list if no matches found.
        """
        target_id = target['id']
        target_name = target['attributes'].get('display_name', 'Unknown Name')
        org_id = target['relationships']['organization']['data']['id']
        
        # 1. Create the AI-BOM Job
        try:
            post_url = f"{self.api_url}/rest/orgs/{org_id}/ai_boms?version={self.api_version}"
            payload = {
                "data": {
                    "type": "ai_bom_scm_bundle",
                    "attributes": {"target_id": target_id}
                }
            }
            response = requests.post(post_url, headers=self.headers, json=payload)
            
            # Some targets might not be compatible; we'll skip them.
            if response.status_code == 422: # Unprocessable Entity
                 logging.debug(f"Skipping '{target_name}': Incompatible target type.")
                 return []

            response.raise_for_status()
            post_data = response.json()
            logging.debug(f"  > Post data: {post_data}")

            job_url = f"{self.api_url}{post_data['links']['self']}" # The URL to poll

            status = post_data['data']['attributes']['status']
            logging.debug(f"  > Job created. Initial status: {status}")

        except requests.exceptions.RequestException as e:
            logging.debug(f"  > Error creating job for '{target_name}': {e}", file=sys.stderr)
            return []

        # 2. Poll for Job Completion
        while status not in ["finished", "errored"]:
            time.sleep(2) # Be kind to the API, wait before checking again
            try:
                logging.debug(f"  > Requesting URL: {job_url}")
                response = requests.get(job_url, headers=self.headers, params={'version': self.api_version}, allow_redirects=False)            
                response.raise_for_status()
                response_data = response.json()
                logging.debug(f"  > Response data: {response_data}")
                
                status = response_data['data']['attributes']['status']
                logging.debug(f"  > Polling... status is now: {status}")
            except requests.exceptions.RequestException as e:
                logging.debug(f"  > Error polling job for '{target_name}': {e}", file=sys.stderr)
                return []

        if status == "errored":
            print(f"  > Job failed for '{target_name}'.", file=sys.stderr)
            return []

        # 3. Get the final AI-BOM and search for the keyword
        # Note that the job_url redirects to the bom get url when it is finished
        # {self.api_url}/rest/orgs/{self.org_id}/ai_boms/{bom_id}?version={self.api_version}
        try:
            logging.debug(f"  > Requesting final BOM URL: {job_url}")
            final_response = requests.get(job_url, headers=self.headers, params={'version': self.api_version}, allow_redirects=True)
            final_response.raise_for_status()
            logging.debug(f"  > Final BOM response: {final_response.json()}")

            return final_response.json()
                
        except requests.exceptions.RequestException as e:
            logging.debug(f"  > Error fetching final BOM for '{target_name}': {e}", file=sys.stderr)
            return []

    def process_target_and_search(self, target, search_keyword):
        aibom = self.process_target(target)

        bom_content = str(aibom)
            
        # Split search terms by comma and check for matches
        search_terms = [term.strip().lower() for term in search_keyword.split(',')]
        bom_content_lower = bom_content.lower()
        
        matched_terms = []
        for term in search_terms:
            if term in bom_content_lower:
                logging.debug(f"  > Term '{term}' found in BOM content.")
                matched_terms.append(term)
        
        if matched_terms:
            logging.debug(f"  > Found terms: {matched_terms}")
        else:
            logging.debug(f"  > None of the terms {search_terms} found in BOM content.")
        
        return matched_terms