import os
import sys
import logging
from .api import SnykAIBomAPIClient
from .config import Config

# --- Main Execution ---
def search(search_keyword: str = None, debug: bool = False):
    """Main entry point for the console script."""
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
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
    config = Config(
        api_token=SNYK_TOKEN,
        org_id=SNYK_ORG_ID,
        api_url=SNYK_API_URL
    )

    scanner = SnykAIBomAPIClient(config)
    
    # if not search_keyword:
    #     search_keyword = args.search_keyword
    
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
        if integration_type in config.supported_integrations:
            # We now call our complete function from steps 3 & 4
            matched_terms = scanner.process_target_and_search(target, search_keyword)
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

