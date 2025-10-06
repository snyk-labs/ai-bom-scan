import sys
import json
import time
from typing import Optional, Set

import click
import yaml
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.status import Status

from .config import Config
from .api import SnykAIBomAPIClient
from .utils.output import display_aibom_summary_all
from .utils.html import generate_html_report
from .search import search as search_command

console = Console()


def load_policy_file(policy_file_path: str) -> Set[str]:
    """
    Load and parse a YAML policy file to extract rejected models.
    
    Args:
        policy_file_path: Path to the YAML policy file
        
    Returns:
        Set of rejected model names
        
    Raises:
        click.ClickException: If the policy file cannot be parsed or is invalid
    """
    try:
        with open(policy_file_path, 'r') as f:
            policy_data = yaml.safe_load(f)
        
        if not isinstance(policy_data, dict):
            raise click.ClickException(f"Policy file must contain a YAML dictionary, got {type(policy_data)}")
        
        if 'reject' not in policy_data:
            raise click.ClickException("Policy file must contain a 'reject' key")
        
        reject_list = policy_data['reject']
        if not isinstance(reject_list, list):
            raise click.ClickException("'reject' key must contain a list of model names")
        
        # Convert to set for efficient lookup and normalize names
        rejected_models = set()
        for model in reject_list:
            if not isinstance(model, str):
                raise click.ClickException(f"All rejected models must be strings, got {type(model)}")
            rejected_models.add(model.strip().lower())
        
        return rejected_models
        
    except yaml.YAMLError as e:
        raise click.ClickException(f"Failed to parse YAML policy file: {e}")
    except FileNotFoundError:
        raise click.ClickException(f"Policy file not found: {policy_file_path}")
    except Exception as e:
        raise click.ClickException(f"Error reading policy file: {e}")


@click.group()
@click.version_option()
@click.option(
    "--api-token",
    envvar="SNYK_TOKEN",
    help="Snyk API token (can also be set via SNYK_TOKEN env var)",
)
@click.option(
    "--org-id",
    envvar="SNYK_ORG_ID",
    help="Snyk Organization ID (can also be set via SNYK_ORG_ID env var)",
)
@click.option(
    "--api-url",
    envvar="SNYK_API_URL",
    default="https://api.snyk.io",
    help="Snyk API base URL (defaults to https://api.snyk.io)",
)
@click.option(
    "--group-id",
    envvar="SNYK_GROUP_ID", 
    type=str,
    help="Snyk Group ID (can also be set via SNYK_GROUP_ID env var)",
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug logging",
)
@click.pass_context
def cli(ctx: click.Context, api_token: Optional[str], org_id: Optional[str], group_id: Optional[str],
        api_url: str, debug: bool) -> None:
    """
    ai-bom-scan: CLI tool for generating AI Bill of Materials using Snyk API
    
    This tool helps you create AI BOMs for your projects using Snyk's AI-BOM API.
    """
    # Ensure context object exists
    ctx.ensure_object(dict)
    
    # Store configuration in context
    config = Config(
        api_token=api_token,
        org_id=org_id,
        group_id=group_id,
        api_url=api_url,
        debug=debug
    )
    
    if not group_id and not org_id:
        console.print("[bold red]Error:[/bold red] Either --group-id or --org-id is required.")
        sys.exit(1)
    
    ctx.obj["config"] = config
    
    if debug:
        console.print("[bold blue]Debug mode enabled[/bold blue]")


@cli.command()
@click.option(
    "--output",
    "-o",
    "--json",
    type=click.Path(),
    help="Output file path for AI-BOMs",
)
@click.option(
    "--html",
    type=click.Path(),
    help="Output file path for HTML report",
)
@click.option(
    "--include",
    "-i",
    type=str,
    help="Comma-separated list of AI component types to include in the summary (e.g., 'ML Model,Application,Library')",
)
@click.option(
    "--policy-file",
    type=click.Path(exists=True, readable=True),
    help="Path to YAML policy file containing list of forbidden models",
)
@click.option(
    "--group-by",
    type=click.Choice(['component', 'repo'], case_sensitive=False),
    default='component',
    help="Group output by 'component' (default) or 'repo'",
)
@click.pass_context
def scan(
    ctx: click.Context,
    output: Optional[str],
    html: Optional[str],
    include: Optional[str],
    policy_file: Optional[str],
    group_by: str,
) -> None:
    """
    Create a new AI-BOM scan
    
    This command triggers a scan of all targets in the given Snyk organization.
    """

    config = ctx.obj["config"]
    
    # Load policy file if provided
    rejected_models = None
    if policy_file:
        try:
            rejected_models = load_policy_file(policy_file)
            console.print(f"[bold blue]📋 Policy file loaded: {len(rejected_models)} forbidden models[/bold blue]")
        except click.ClickException as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            sys.exit(1)
    
    # Validate required configuration
    if not config.api_token:
        console.print("[bold red]Error:[/bold red] API token is required. "
                     "Set SNYK_TOKEN environment variable or use --api-token option.")
        sys.exit(1)
        
    if not config.org_id and not config.group_id:
        console.print("[bold red]Error:[/bold red] Organization ID or Group ID is required. "
                     "Set SNYK_ORG_ID or SNYK_GROUP_ID environment variable, or use --org-id or --group-id option.")
        sys.exit(1)
    
    # Create API client
    # client = SnykAIBOMClient(config)
    client = SnykAIBomAPIClient(config)
    try:
        # Animated status while retrieving targets
        with Status("[bold green]Retrieving targets...", spinner="dots") as status:
            all_targets = client.get_all_targets()
            all_aiboms = []
            
        if not all_targets:
            console.print("[bold red]❌ Could not retrieve any targets. Exiting.[/bold red]")
            sys.exit(1)
            
        if config.group_id:
            console.print(f"[bold blue]🎯 Found {len(all_targets)} total targets in the group {config.group_id}.[/bold blue]")
        else:
            console.print(f"[bold blue]🎯 Found {len(all_targets)} total targets in the organization {config.org_id}.[/bold blue]")
        
        # Filter targets to only supported ones for the progress bar
        supported_targets = []
        for target in all_targets:
            integration_type = target.get('relationships', {}).get('integration', {}).get('data', {}).get('attributes', {}).get('integration_type')
            if integration_type in ['github', 'github-enterprise', 'github-cloud-app', 'github-server-app', 'gitlab', 'azure-repos', 'bitbucket-cloud', 'bitbucket-server', 'bitbucket-cloud-app']:
                supported_targets.append(target)
        
        console.print(f"[bold cyan]📊 Processing {len(supported_targets)} supported targets...[/bold cyan]")
        
        # Progress bar for processing targets
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            
            main_task = progress.add_task("Scanning targets...", total=len(all_targets))
            
            for i, target in enumerate(all_targets):
                target_name = target['attributes'].get('display_name', 'Unknown Name')
                progress.update(main_task, description=f"Processing: {target_name[:30]}...")
                
                integration_type = target.get('relationships', {}).get('integration', {}).get('data', {}).get('attributes', {}).get('integration_type')
                if integration_type in ['github', 'github-enterprise', 'github-cloud-app', 'github-server-app', 'gitlab', 'azure-repos', 'bitbucket-cloud', 'bitbucket-server', 'bitbucket-cloud-app']:
                    aibom_data = client.process_target(target)
                    if aibom_data:
                        component_count = len(aibom_data['data']['attributes']['components']) - 1
                        console.print(f"  [bold green]✅[/bold green] {target_name}: [bold yellow]{component_count}[/bold yellow] AI components")
                        all_aiboms.append({ 
                            'target_name': target_name,
                            'aibom_data': aibom_data
                        })
                    else:
                        console.print(f"  [bold red]❌[/bold red] Error scanning {target_name}")
                else:
                    # Skip other target types like container images or manual uploads
                    console.print(f"  [dim]⏭️  Skipping {target_name} (unsupported type)[/dim]")
                
                progress.advance(main_task)
        
        # Animated completion message
        with console.status("[bold green]Generating comprehensive report...", spinner="arc"):
            time.sleep(1)  # Simulate processing time
        
        console.print("\n[bold green]🎉 Scan Complete![/bold green]")
        console.print("[bold blue]" + "=" * 50 + "[/bold blue]")
        
        # Display comprehensive summary of all AI components
        if all_aiboms:
            display_aibom_summary_all(all_aiboms, include_types=include, rejected_models=rejected_models, group_by=group_by)
        else:
            console.print("[bold yellow]⚠️  No AI components found in any targets.[/bold yellow]")

        if output:
            output_data = {"all_aibom_data": all_aiboms}
            with open(output, 'w') as f:
                json.dump(output_data, f, indent=4)
            console.print(f"[bold green]📄 JSON report saved to: {output}[/bold green]")
        
        if html:
            html_content = generate_html_report(all_aiboms, include_types=include, rejected_models=rejected_models, group_by=group_by)
            with open(html, 'w', encoding='utf-8') as f:
                f.write(html_content)
            console.print(f"[bold green]🌐 HTML report saved to: {html}[/bold green]")
            
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        if config.debug:
            console.print_exception()
        sys.exit(1)

@cli.command()
@click.argument("search_keyword", type=str)
@click.option("--debug", is_flag=True, help="Enable debug output")
def search(search_keyword: str, debug: bool) -> None:
    """Search for AI models in Snyk targets"""
    search_command(search_keyword, debug)


def main() -> None:
    """Main entry point for the CLI"""
    cli()


def scan_main() -> None:
    """Direct entry point for the scan command"""
    sys.argv = ["aibom", "scan"] + sys.argv[1:]
    cli()

def search_main() -> None:
    """Direct entry point for the scan command"""
    sys.argv = ["aibom", "search"] + sys.argv[1:]
    cli()


if __name__ == "__main__":
    main()
