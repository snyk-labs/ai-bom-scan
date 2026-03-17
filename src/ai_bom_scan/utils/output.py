from typing import Optional, Set
import time
from rich.console import Console
from rich.table import Table

console = Console()

def display_aibom_summary_all(all_aiboms: list, include_types: Optional[str] = None, rejected_models: Optional[Set[str]] = None, group_by: str = 'component') -> None:
    """Display a comprehensive summary of all AI components across all targets"""
    if not all_aiboms:
        console.print("[yellow]No AI components found across any targets.[/yellow]")
        return
    
    # Parse and normalize include types if provided
    included_internal_types = None
    if include_types:
        # Create mapping from user-friendly names to internal types (case-insensitive)
        user_type_mapping = {
            'ml model': 'machine-learning-model',
            'ml models': 'machine-learning-model', 
            'machine learning model': 'machine-learning-model',
            'machine learning models': 'machine-learning-model',
            'dataset': 'data',
            'datasets': 'data',
            'data': 'data',
            'library': 'library',
            'libraries': 'library',
            'application': 'application',
            'applications': 'application',
            'app': 'application',
            'apps': 'application'
        }
        
        # Parse comma-separated types and convert to internal format
        include_list = [t.strip().lower() for t in include_types.split(',')]
        included_internal_types = set()
        
        for user_type in include_list:
            if user_type in user_type_mapping:
                included_internal_types.add(user_type_mapping[user_type])
            else:
                # Try direct match with internal types (for backward compatibility)
                if user_type in ['machine-learning-model', 'data', 'library', 'application']:
                    included_internal_types.add(user_type)
                else:
                    console.print(f"[bold yellow]Warning:[/bold yellow] Unknown component type '{user_type}' will be ignored")
        
        if not included_internal_types:
            console.print("[bold red]Error:[/bold red] No valid component types specified")
            return
    
    # Animated header
    with console.status("[bold green]Preparing AI Components Summary...", spinner="aesthetic"):
        time.sleep(0.5)
    
    if group_by.lower() == 'repo':
        console.print("\n[bold green]🤖 AI Components Summary - Grouped by Repository 🎯[/bold green]")
    else:
        console.print("\n[bold green]🤖 AI Components Summary - All Targets 🎯[/bold green]")
    
    if group_by.lower() == 'repo':
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Repository", style="yellow", no_wrap=True, min_width=30)
        table.add_column("AI Component", style="cyan", no_wrap=False, min_width=40)
        table.add_column("Type", style="blue", no_wrap=True, min_width=15)
        table.add_column("Locations", style="dim", no_wrap=False, min_width=30)
    else:
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("AI Component", style="cyan", no_wrap=False, min_width=40)
        table.add_column("Target Name", style="yellow", no_wrap=True, min_width=25)
        table.add_column("Type", style="blue", no_wrap=True, min_width=15)
        table.add_column("Locations", style="dim", no_wrap=False, min_width=30)
    
    # Collect all AI components across targets
    total_components = 0
    components_data = []
    
    for target_info in all_aiboms:
        target_name = target_info.get('target_name', 'Unknown Target')
        aibom_data = target_info.get('aibom_data', {})
        
        # Handle both old format (data.attributes.components) and new format (components)
        if 'data' in aibom_data:
            components = aibom_data.get('data', {}).get('attributes', {}).get('components', [])
        else:
            components = aibom_data.get('components', [])
        
        for component in components:
            # Skip the Root application component as it's not a real AI component
            if (component.get('name') == 'Root' and 
                component.get('type') == 'application'):
                continue
            
            comp_type = component.get('type', 'unknown')
            
            # Filter by included types if specified
            if included_internal_types and comp_type not in included_internal_types:
                continue
            
            name = component.get('name', 'Unknown Component')
            
            # Format component type for better readability
            type_mapping = {
                'machine-learning-model': 'ML Model',
                'data': 'Dataset', 
                'library': 'Library',
                'application': 'Application'
            }
            formatted_type = type_mapping.get(comp_type, comp_type.title())
            
            # Extract location information from evidence
            locations = []
            evidence = component.get('evidence', {})
            occurrences = evidence.get('occurrences', [])
            
            for occurrence in occurrences:
                location = occurrence.get('location', '')
                line = occurrence.get('line', '')
                if location and line:
                    locations.append(f"{location}:{line}")
                elif location:
                    locations.append(location)
            
            # Format locations for display
            if locations:
                location_str = '\n'.join(locations[:3])  # Show max 3 locations
                if len(locations) > 3:
                    location_str += f'\n... and {len(locations) - 3} more'
            else:
                location_str = "No source locations"
            
            components_data.append({
                'name': name,
                'target_name': target_name,
                'type': formatted_type,
                'locations': location_str
            })
            total_components += 1
    
    # Add rows to table based on grouping mode
    if group_by.lower() == 'repo':
        # Group components by repository
        from collections import defaultdict
        repo_groups = defaultdict(list)
        for component in components_data:
            repo_groups[component['target_name']].append(component)
        
        # Sort repositories and components within each repo
        for repo_name in sorted(repo_groups.keys(), key=str.lower):
            components = sorted(repo_groups[repo_name], key=lambda x: x['name'].lower())
            
            # Add first component with repo name
            first_component = components[0]
            table.add_row(repo_name, first_component['name'], first_component['type'], first_component['locations'])
            
            # Add remaining components with empty repo column
            for component in components[1:]:
                table.add_row("", component['name'], component['type'], component['locations'])
    else:
        # Sort by component name, then by repository name (original behavior)
        components_data.sort(key=lambda x: (x['name'].lower(), x['target_name'].lower()))
        for component in components_data:
            table.add_row(component['name'], component['target_name'], component['type'], component['locations'])
    
    # Display the completed table
    console.print(table)
    
    # Animated completion statistics
    with console.status("[bold cyan]Calculating statistics...", spinner="moon"):
        time.sleep(0.3)
        
        # Print summary by type
        component_types = {}
        for target_info in all_aiboms:
            target_name = target_info.get('target_name', 'Unknown Target')
            aibom_data = target_info.get('aibom_data', {})
            
            if 'data' in aibom_data:
                components = aibom_data.get('data', {}).get('attributes', {}).get('components', [])
            else:
                components = aibom_data.get('components', [])
            
            for component in components:
                if (component.get('name') == 'Root' and 
                    component.get('type') == 'application'):
                    continue
                
                comp_type = component.get('type', 'unknown')
                
                # Filter by included types if specified
                if included_internal_types and comp_type not in included_internal_types:
                    continue
                
                component_types[comp_type] = component_types.get(comp_type, 0) + 1
    
    # Statistics panel
    console.print(f"\n[bold green]📈 Total AI Components Found: {total_components}[/bold green]")
    
    if component_types:
        console.print("\n[bold cyan]📊 Component Types Breakdown:[/bold cyan]")
        
        # Create a mini table for component types
        stats_table = Table(show_header=True, header_style="bold blue", box=None)
        stats_table.add_column("Type", style="cyan")
        stats_table.add_column("Count", style="green", justify="right")
        
        for comp_type, count in sorted(component_types.items()):
            type_mapping = {
                'machine-learning-model': '🧠 ML Models',
                'data': '📊 Datasets', 
                'library': '📚 Libraries',
                'application': '🔧 Applications'
            }
            formatted_type = type_mapping.get(comp_type, f"🔧 {comp_type.title()}")
            stats_table.add_row(formatted_type, str(count))
        
        console.print(stats_table)
    
    # Policy validation and forbidden models table
    if rejected_models:
        _display_policy_validation(all_aiboms, rejected_models)


def _display_policy_validation(all_aiboms: list, rejected_models: Set[str]) -> None:
    """Display policy validation results and forbidden models table"""
    # Collect all forbidden models found in the scan
    forbidden_found = []
    
    for target_info in all_aiboms:
        target_name = target_info.get('target_name', 'Unknown Target')
        aibom_data = target_info.get('aibom_data', {})
        
        # Handle both old format (data.attributes.components) and new format (components)
        if 'data' in aibom_data:
            components = aibom_data.get('data', {}).get('attributes', {}).get('components', [])
        else:
            components = aibom_data.get('components', [])
        
        for component in components:
            # Skip the Root application component as it's not a real AI component
            if (component.get('name') == 'Root' and 
                component.get('type') == 'application'):
                continue
            
            # Only check ML models for policy violations
            if component.get('type') != 'machine-learning-model':
                continue
            
            model_name = component.get('name', '').strip().lower()
            
            # Check if this model is in the rejected list
            if model_name in rejected_models:
                # Extract location information from evidence
                locations = []
                evidence = component.get('evidence', {})
                occurrences = evidence.get('occurrences', [])
                
                for occurrence in occurrences:
                    location = occurrence.get('location', '')
                    line = occurrence.get('line', '')
                    if location and line:
                        locations.append(f"{location}:{line}")
                    elif location:
                        locations.append(location)
                
                # Format locations for display
                if locations:
                    location_str = '\n'.join(locations[:3])  # Show max 3 locations
                    if len(locations) > 3:
                        location_str += f'\n... and {len(locations) - 3} more'
                else:
                    location_str = "No source locations"
                
                forbidden_found.append({
                    'model_name': component.get('name', 'Unknown Model'),
                    'target_name': target_name,
                    'locations': location_str
                })
    
    # Display results
    console.print("\n[bold red]🚫 Policy Validation Results[/bold red]")
    console.print("[bold blue]" + "=" * 50 + "[/bold blue]")
    
    if forbidden_found:
        # Create table for forbidden models
        forbidden_table = Table(show_header=True, header_style="bold red")
        forbidden_table.add_column("Forbidden Model", style="red", no_wrap=False, min_width=40)
        forbidden_table.add_column("Target Name", style="yellow", no_wrap=True, min_width=25)
        forbidden_table.add_column("Locations", style="dim", no_wrap=False, min_width=30)
        
        for item in forbidden_found:
            forbidden_table.add_row(
                item['model_name'],
                item['target_name'],
                item['locations']
            )
        
        console.print(forbidden_table)
        console.print(f"\n[bold red]❌ Policy Violation: {len(forbidden_found)} forbidden model(s) found![/bold red]")
    else:
        console.print("[bold green]✅ Policy Compliance: No forbidden models found in the scan![/bold green]")
        console.print("[bold blue]📋 All models in use comply with the provided policy.[/bold blue]")

