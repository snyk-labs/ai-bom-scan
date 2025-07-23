import os
import sys
import time
import requests
import argparse
import logging

class SnykAIBomScanner:
    """Snyk AI-BOM scanner client."""
    
    def __init__(self, api_url, org_id, token, api_version='2025-07-22'):
        self.api_url = api_url
        self.org_id = org_id
        self.api_version = api_version
        self.headers = {
            'Content-Type': 'application/vnd.api+json',
            'Authorization': f'token {token}'
        }
    
    def get_all_targets(self):
        """
        Fetches all targets from a Snyk organization, handling pagination.
        """
        targets = []
        # Start with the first page URL, limiting to 100 results per page
        url = f"{self.api_url}/rest/orgs/{self.org_id}/targets?version={self.api_version}&limit=100"
        
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
                    print(f"Fetching next page of targets...", file=sys.stderr)
                else:
                    url = None # End the loop

            except requests.exceptions.RequestException as e:
                print(f"Error fetching targets: {e}", file=sys.stderr)
                return None
        
        return targets

    def process_target(self, search_keyword, target):
        """
        Generates and searches an AI-BOM for a single target.
        
        Returns:
            list: List of matched search terms, or empty list if no matches found.
        """
        target_id = target['id']
        target_name = target['attributes'].get('display_name', 'Unknown Name')
        
        print(f"Processing Target: {target_name} ({target_id})")

        # 1. Create the AI-BOM Job
        try:
            post_url = f"{self.api_url}/rest/orgs/{self.org_id}/ai_boms?version={self.api_version}"
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

            bom_content = final_response.text
            
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
                
        except requests.exceptions.RequestException as e:
            logging.debug(f"  > Error fetching final BOM for '{target_name}': {e}", file=sys.stderr)
            return []


# --- Main Execution ---
def main():
    """Main entry point for the console script."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Scan Snyk organization targets for AI-BOM keywords")
    parser.add_argument("search_keyword", help="The keyword(s) to search for in the AI-BOM (comma-separated for multiple terms)")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format='%(message)s'
    )
    
    # Get required values from environment variables
    SNYK_API_URL = os.getenv("SNYK_API_URL", "https://api.snyk.io")
    SNYK_ORG_ID = os.getenv("SNYK_ORG_ID")
    SNYK_TOKEN = os.getenv("SNYK_TOKEN")
    
    # Pre-flight checks
    if not all([SNYK_ORG_ID, SNYK_TOKEN]):
        print("Error: Please set SNYK_ORG_ID and SNYK_TOKEN environment variables.", file=sys.stderr)
        sys.exit(1)
    
    # Setup API components
    scanner = SnykAIBomScanner(SNYK_API_URL, SNYK_ORG_ID, SNYK_TOKEN)
    
    search_keyword = args.search_keyword
    
    # Format the search terms for display
    search_terms_display = [term.strip() for term in search_keyword.split(',')]
    if len(search_terms_display) == 1:
        search_display = f"'{search_terms_display[0]}'"
    else:
        terms_formatted = ', '.join([f"'{term}'" for term in search_terms_display])
        search_display = f"any of: {terms_formatted}"
    
    print(f"Starting scan to find targets using {search_display}...")
    
    all_targets = scanner.get_all_targets()
    
    if not all_targets:
        print("Could not retrieve any targets. Exiting.", file=sys.stderr)
        sys.exit(1)
        
    print(f"Found {len(all_targets)} total targets in the organization.")
    
    found_in_targets = []
    
    for target in all_targets:
        # Get integration type from the nested structure
        integration_type = target.get('relationships', {}).get('integration', {}).get('data', {}).get('attributes', {}).get('integration_type')
        if integration_type in ['github', 'github-enterprise', 'gitlab', 'azure-repos', 'bitbucket-cloud']:
            # We now call our complete function from steps 3 & 4
            matched_terms = scanner.process_target(search_keyword, target)
            if matched_terms: 
                target_name = target['attributes'].get('display_name', target['id'])
                found_in_targets.append({'name': target_name, 'terms': matched_terms})
                print(f"  ✅ FOUND match in {target_name}!")
        else:
            # Skip other target types like container images or manual uploads
            target_name = target['attributes'].get('display_name', 'Unknown Name')
            logging.debug(f"Skipping Target: {target_name} (Integration: {integration_type})")

    # --- Final Report ---
    print("Scan Complete")
    print("=" * 50)
    
    if found_in_targets:
        target_count = len(found_in_targets)
        target_word = "target" if target_count == 1 else "targets"
        
        print(f"✅ Found matches in {target_count} {target_word}:")
        for target in found_in_targets:
            terms_str = ','.join(target['terms'])
            print(f"   • {target['name']} ({terms_str})")
    else:
        print(f"ℹ️  No matches for {search_display} found in any scanned target.")
    
    print("=" * 50)

if __name__ == "__main__":
    main()