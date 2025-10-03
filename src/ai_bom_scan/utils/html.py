from typing import Optional, Set
import time

def generate_html_report(all_aiboms: list, include_types: Optional[str] = None, rejected_models: Optional[Set[str]] = None, group_by: str = 'component') -> str:
    """Generate an HTML report of all AI components across all targets"""
    if not all_aiboms:
        return _generate_empty_html_report()
    
    # Parse and normalize include types if provided (same logic as _display_aibom_summary_all)
    included_internal_types = None
    if include_types:
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
        
        include_list = [t.strip().lower() for t in include_types.split(',')]
        included_internal_types = set()
        
        for user_type in include_list:
            if user_type in user_type_mapping:
                included_internal_types.add(user_type_mapping[user_type])
            else:
                if user_type in ['machine-learning-model', 'data', 'library', 'application']:
                    included_internal_types.add(user_type)
    
    # Collect all AI components across targets
    components_data = []
    component_types = {}
    total_components = 0
    
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
                location_str = '; '.join(locations[:5])  # Show max 5 locations
                if len(locations) > 5:
                    location_str += f' ... and {len(locations) - 5} more'
            else:
                location_str = "No source locations"
            
            components_data.append({
                'name': name,
                'target_name': target_name,
                'type': formatted_type,
                'locations': location_str
            })
            
            component_types[comp_type] = component_types.get(comp_type, 0) + 1
            total_components += 1
    
    # Generate HTML content
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Bill of Materials Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }}
        .header p {{
            margin: 10px 0 0 0;
            opacity: 0.9;
            font-size: 1.1em;
        }}
        .stats {{
            display: flex;
            justify-content: space-around;
            padding: 20px;
            background: #f8f9fa;
            border-bottom: 1px solid #e9ecef;
        }}
        .stat-item {{
            text-align: center;
        }}
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }}
        .stat-label {{
            color: #666;
            font-size: 0.9em;
            margin-top: 5px;
        }}
        .table-container {{
            padding: 20px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th {{
            background: #667eea;
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
        }}
        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #e9ecef;
        }}
        .repo-group-first {{
            border-top: 2px solid #667eea;
        }}
        .repo-group-first td:first-child {{
            border-top: 2px solid #667eea;
            font-weight: bold;
        }}
        .repo-group-continuation {{
            border-bottom: none !important;
            vertical-align: top;
        }}
        .repo-group-last td:first-child {{
            border-bottom: 1px solid #667eea;
        }}
        .repo-group-continuation {{
            border-left: none;
            border-right: 1px solid #e9ecef;
        }}
        .repo-group-continuation:first-child {{
            border-left: 1px solid #e9ecef;
        }}
        tr:hover {{
            background-color: #f8f9fa;
        }}
        .repo-empty {{
            border-bottom: none !important;
        }}
        .type-badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .type-ml-model {{
            background: #e3f2fd;
            color: #1976d2;
        }}
        .type-dataset {{
            background: #f3e5f5;
            color: #7b1fa2;
        }}
        .type-library {{
            background: #e8f5e8;
            color: #388e3c;
        }}
        .type-application {{
            background: #fff3e0;
            color: #f57c00;
        }}
        .locations {{
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 0.9em;
            color: #666;
            max-width: 300px;
            word-break: break-all;
        }}
        .footer {{
            padding: 20px;
            text-align: center;
            color: #666;
            border-top: 1px solid #e9ecef;
            background: #f8f9fa;
        }}
        .no-data {{
            text-align: center;
            padding: 60px 20px;
            color: #666;
        }}
        .no-data h2 {{
            color: #999;
            margin-bottom: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 AI Bill of Materials Report</h1>
            <p>Comprehensive analysis of AI components across all targets</p>
        </div>
        
        <div class="stats">
            <div class="stat-item">
                <div class="stat-number">{total_components}</div>
                <div class="stat-label">Total AI Components</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{len(all_aiboms)}</div>
                <div class="stat-label">Targets Scanned</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{len(component_types)}</div>
                <div class="stat-label">Component Types</div>
            </div>
        </div>
        
        <div class="table-container">
            {_generate_policy_validation_html(all_aiboms, rejected_models) if rejected_models else ''}
            
            {_generate_component_types_breakdown_html(component_types)}
            
            {_generate_components_table_html(components_data, group_by) if components_data else _generate_no_data_html()}
            
            {_generate_repositories_list_html(all_aiboms)}
        </div>
        
        <div class="footer">
            <p>Generated by ai-bom-scan • {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>"""
    
    return html_content

def _generate_empty_html_report() -> str:
    """Generate HTML report when no AI components are found"""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Bill of Materials Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }}
        .no-data {{
            text-align: center;
            padding: 60px 20px;
            color: #666;
        }}
        .no-data h2 {{
            color: #999;
            margin-bottom: 10px;
        }}
        .footer {{
            padding: 20px;
            text-align: center;
            color: #666;
            border-top: 1px solid #e9ecef;
            background: #f8f9fa;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 AI Bill of Materials Report</h1>
            <p>Comprehensive analysis of AI components across all targets</p>
        </div>
        
        <div class="no-data">
            <h2>⚠️ No AI Components Found</h2>
            <p>No AI components were detected in any of the scanned targets.</p>
        </div>
        
        <div class="footer">
            <p>Generated by ai-bom-scan • {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>"""

def _generate_component_types_breakdown_html(component_types: dict) -> str:
    """Generate HTML for component types breakdown"""
    if not component_types:
        return ""
    
    type_mapping = {
        'machine-learning-model': ('🧠 ML Models', 'type-ml-model'),
        'data': ('📊 Datasets', 'type-dataset'), 
        'library': ('📚 Libraries', 'type-library'),
        'application': ('🔧 Applications', 'type-application')
    }
    
    breakdown_html = '<h3>📊 Component Types Breakdown</h3><div style="display: flex; gap: 20px; margin-bottom: 20px; flex-wrap: wrap;">'
    
    for comp_type, count in sorted(component_types.items()):
        formatted_type, css_class = type_mapping.get(comp_type, (f"🔧 {comp_type.title()}", 'type-application'))
        breakdown_html += f'''
        <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; min-width: 120px;">
            <div style="font-size: 1.5em; font-weight: bold; color: #667eea;">{count}</div>
            <div style="color: #666; font-size: 0.9em;">{formatted_type}</div>
        </div>'''
    
    breakdown_html += '</div>'
    return breakdown_html

def _generate_components_table_html(components_data: list, group_by: str = 'component') -> str:
    """Generate HTML table for components data"""
    if not components_data:
        return _generate_no_data_html()
    
    # Sort data based on grouping mode
    if group_by.lower() == 'repo':
        components_data.sort(key=lambda x: (x['target_name'].lower(), x['name'].lower()))
        table_html = '''
        <h3>🔍 AI Components Details - Grouped by Repository</h3>
        <table>
            <thead>
                <tr>
                    <th>Repository</th>
                    <th>AI Component</th>
                    <th>Type</th>
                    <th>Locations</th>
                </tr>
            </thead>
            <tbody>'''
    else:
        components_data.sort(key=lambda x: (x['name'].lower(), x['target_name'].lower()))
        table_html = '''
        <h3>🔍 AI Components Details</h3>
        <table>
            <thead>
                <tr>
                    <th>AI Component</th>
                    <th>Target Name</th>
                    <th>Type</th>
                    <th>Locations</th>
                </tr>
            </thead>
            <tbody>'''
    
    if group_by.lower() == 'repo':
        # Group components by repository
        from collections import defaultdict
        repo_groups = defaultdict(list)
        for component in components_data:
            repo_groups[component['target_name']].append(component)
        
        # Sort repositories and components within each repo
        for repo_name in sorted(repo_groups.keys(), key=str.lower):
            components = sorted(repo_groups[repo_name], key=lambda x: x['name'].lower())
            
            for i, component in enumerate(components):
                # Determine CSS class for type badge
                type_class = 'type-application'  # default
                if 'ML Model' in component['type']:
                    type_class = 'type-ml-model'
                elif 'Dataset' in component['type']:
                    type_class = 'type-dataset'
                elif 'Library' in component['type']:
                    type_class = 'type-library'
                
                if i == 0:
                    # First component shows repo name with group styling
                    table_html += f'''
                        <tr class="repo-group-first">
                            <td><strong>{repo_name}</strong></td>
                            <td>{component['name']}</td>
                            <td><span class="type-badge {type_class}">{component['type']}</span></td>
                            <td class="locations">{component['locations']}</td>
                        </tr>'''
                else:
                    # Subsequent components have empty repo column with no border
                    table_html += f'''
                        <tr>
                            <td class="repo-empty"></td>
                            <td>{component['name']}</td>
                            <td><span class="type-badge {type_class}">{component['type']}</span></td>
                            <td class="locations">{component['locations']}</td>
                        </tr>'''
    else:
        for component in components_data:
            # Determine CSS class for type badge
            type_class = 'type-application'  # default
            if 'ML Model' in component['type']:
                type_class = 'type-ml-model'
            elif 'Dataset' in component['type']:
                type_class = 'type-dataset'
            elif 'Library' in component['type']:
                type_class = 'type-library'
            
            table_html += f'''
                <tr>
                    <td><strong>{component['name']}</strong></td>
                    <td>{component['target_name']}</td>
                    <td><span class="type-badge {type_class}">{component['type']}</span></td>
                    <td class="locations">{component['locations']}</td>
                </tr>'''
    
    table_html += '''
        </tbody>
    </table>'''
    
    return table_html

def _generate_no_data_html() -> str:
    """Generate HTML for when no components are found"""
    return '''
    <div class="no-data">
        <h2>⚠️ No AI Components Found</h2>
        <p>No AI components were detected in any of the scanned targets.</p>
    </div>'''


def _generate_policy_validation_html(all_aiboms: list, rejected_models: Set[str]) -> str:
    """Generate HTML for policy validation results"""
    # Collect all forbidden models found in the scan (same logic as _display_policy_validation)
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
                    location_str = '; '.join(locations[:5])  # Show max 5 locations
                    if len(locations) > 5:
                        location_str += f' ... and {len(locations) - 5} more'
                else:
                    location_str = "No source locations"
                
                forbidden_found.append({
                    'model_name': component.get('name', 'Unknown Model'),
                    'target_name': target_name,
                    'locations': location_str
                })
    
    # Generate HTML content
    if forbidden_found:
        # Policy violation HTML
        html_content = '''
        <h3 style="color: #d32f2f; margin-top: 30px;">🚫 Policy Validation Results</h3>
        <div style="background: #ffebee; border: 1px solid #f44336; border-radius: 8px; padding: 20px; margin: 20px 0;">
            <h4 style="color: #d32f2f; margin: 0 0 15px 0;">❌ Policy Violation: ''' + str(len(forbidden_found)) + ''' forbidden model(s) found!</h4>
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="background: #f44336; color: white;">
                        <th style="padding: 12px; text-align: left;">Forbidden Model</th>
                        <th style="padding: 12px; text-align: left;">Target Name</th>
                        <th style="padding: 12px; text-align: left;">Locations</th>
                    </tr>
                </thead>
                <tbody>'''
        
        for item in forbidden_found:
            html_content += f'''
                    <tr style="border-bottom: 1px solid #e0e0e0;">
                        <td style="padding: 12px;"><strong style="color: #d32f2f;">{item['model_name']}</strong></td>
                        <td style="padding: 12px;">{item['target_name']}</td>
                        <td style="padding: 12px; font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace; font-size: 0.9em; color: #666;">{item['locations']}</td>
                    </tr>'''
        
        html_content += '''
                </tbody>
            </table>
        </div>'''
        
        return html_content
    else:
        # Policy compliance HTML
        return '''
        <h3 style="color: #2e7d32; margin-top: 30px;">🚫 Policy Validation Results</h3>
        <div style="background: #e8f5e8; border: 1px solid #4caf50; border-radius: 8px; padding: 20px; margin: 20px 0;">
            <h4 style="color: #2e7d32; margin: 0 0 10px 0;">✅ Policy Compliance: No forbidden models found in the scan!</h4>
            <p style="color: #2e7d32; margin: 0;">📋 All models in use comply with the provided policy.</p>
        </div>'''


def _generate_repositories_list_html(all_aiboms: list) -> str:
    """Generate HTML for the list of successfully scanned repositories"""
    if not all_aiboms:
        return ""
    
    # Extract repository names and count AI components for each
    repositories_data = []
    for target_info in all_aiboms:
        target_name = target_info.get('target_name', 'Unknown Target')
        aibom_data = target_info.get('aibom_data', {})
        
        # Handle both old format (data.attributes.components) and new format (components)
        if 'data' in aibom_data:
            components = aibom_data.get('data', {}).get('attributes', {}).get('components', [])
        else:
            components = aibom_data.get('components', [])
        
        # Count AI components (excluding the Root application component)
        ai_component_count = 0
        for component in components:
            if not (component.get('name') == 'Root' and component.get('type') == 'application'):
                ai_component_count += 1
        
        repositories_data.append({
            'name': target_name,
            'ai_component_count': ai_component_count
        })
    
    # Sort repositories by name for consistent ordering
    repositories_data.sort(key=lambda x: x['name'].lower())
    
    # Generate HTML content
    html_content = '''
    <h3 style="color: #1976d2; margin-top: 40px; margin-bottom: 20px;">📁 Successfully Scanned Repositories</h3>
    <div style="background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 8px; padding: 20px; margin: 20px 0;">
        <p style="color: #666; margin: 0 0 15px 0; font-size: 0.95em;">The following repositories were successfully scanned for AI components:</p>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 10px;">'''
    
    for repo in repositories_data:
        html_content += f'''
        <div style="background: white; border: 1px solid #e0e0e0; border-radius: 6px; padding: 12px; display: flex; justify-content: space-between; align-items: center;">
            <span style="font-weight: 500; color: #333;">{repo['name']}</span>
            <span style="background: #e3f2fd; color: #1976d2; padding: 4px 8px; border-radius: 12px; font-size: 0.85em; font-weight: 600;">
                {repo['ai_component_count']} AI component{'' if repo['ai_component_count'] == 1 else 's'}
            </span>
        </div>'''
    
    html_content += '''
        </div>
        <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #e0e0e0; text-align: center;">
            <span style="color: #666; font-size: 0.9em;">
                Total: <strong>''' + str(len(repositories_data)) + '''</strong> repositories scanned
            </span>
        </div>
    </div>'''
    
    return html_content
