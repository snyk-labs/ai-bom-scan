# AI-BOM Scan

A tool to scan Snyk targets for specific components in AI Bills of Materials (AI-BOMs) using the Snyk API.

## Overview

This tool connects to the Snyk API to:
1. Fetch all targets from your Snyk organization
2. Generate AI-BOMs for each target
3. Search for specific keywords/components in those AI-BOMs
4. Report which targets contain the specified components

Perfect for identifying which of your Snyk organization's targets use specific AI frameworks, models, or libraries. Supports searching for multiple terms with OR logic using comma-separated values.

## Prerequisites

- Python 3.8 or higher
- Snyk account with API access
- Snyk organization with imported repositories

## Installation (using uv)

```bash
# Install dependencies
uv sync

# Install the project
uv pip install -e .

# Install and run with uvx
uv tool install git+https://github.com/snyk-labs/aibom-tools
```

## Configuration

Set the required environment variables:

```bash
export SNYK_ORG_ID="your-organization-id"
export SNYK_TOKEN="your-snyk-api-token"

# Optional: Use different Snyk API URL (defaults to https://api.snyk.io)
export SNYK_API_URL="https://api.snyk.io"
```

### Getting Your Snyk Credentials

1. **Snyk Token**: Go to [Snyk Account Settings](https://app.snyk.io/account) → Auth Token
2. **Organization ID**: Found in your Snyk organization URL or API responses

## Usage

### Search

```bash
# Basic usage
aibom search "deepseek"

# Search for multiple terms with OR logic (comma-separated)
aibom search "deepseek,openai"

# Enable debug output
aibom search --debug "pytorch"

# Get help
aibom search --help
```

### Scan

```bash
# Basic usage
aibom scan

# Specify path to HTML output file
aibom scan --html report.html

# Specify path to JSON output file
aibom scan --json output.json

# Group by AI component (default behavior)
aibom scan --group-by component

# Group by repository - shows each repository with its AI components grouped together
aibom scan --group-by repo

# Generate HTML report grouped by repository
aibom scan --group-by repo --html report.html

# Get help
aibom scan --help
```

Available grouping options:
- component (default): Groups output by AI component name
- repo: Groups output by repository, showing each repository with its AI components listed underneath


You can use a YAML policy file to define forbidden AI models that should be flagged during the scan:

```bash
# Use policy file to validate against forbidden models
aibom scan --policy-file policy.yaml
```

#### Policy File Format

Create a YAML file with the following structure:

```yaml
reject:
  - claude-3-5-sonnet-20240620
  - gpt-3.5-turbo
  - gpt-4
  - llama-2-7b
```

An example policy file (`policy-example.yaml`) is included in the repository for reference.

#### Output Format

Using --output or -o can be used to output a JSON file. The AIBOM results are returned in the standard Snyk API JSON format:

```
{
    "all_aibom_data": [
        {
            "target_name": "repo_org/name",
            "aibom_data": {
              ...
            }
        }
    ]
}
```

### Using uv run (without installation)

```bash
# Run directly with uv
uv run python main.py "deepseek"

# With debug mode
uv run python main.py --debug "deepseek"
```

## Examples

### Search for single term
```bash
aibom search "deepseek"
```

Output:
```
Starting scan to find targets using 'deepseek'...
Found 45 total targets in the organization.

Scan Complete
==================================================
✅ Found matches in 3 targets:
   • my-org/ml-project (deepseek)
   • my-org/data-science-tools (deepseek)
   • my-org/ai-experiments (deepseek)
   ...
==================================================
```

### Search for multiple terms (OR logic)
```bash
aibom search "deepseek,openai,anthropic"
```

Output:
```
Starting scan to find targets using any of: 'deepseek', 'openai', 'anthropic'...
Found 45 total targets in the organization.

Scan Complete
==================================================
✅ Found matches in 8 targets:
   • my-org/ml-project (openai)
   • my-org/chatbot-service (openai,anthropic)
   • my-org/ai-experiments (deepseek)
   • my-org/content-generator (openai)
   • my-org/voice-assistant (anthropic)
   • my-org/smart-recommendations (openai,deepseek)
   • my-org/language-tools (anthropic)
   • my-org/research-prototype (deepseek,openai)
==================================================
```

### Search with debug information
```bash
aibom search --debug "openai,claude"
```

This will show detailed information about:
- API requests being made
- Job status updates
- Processing details for each repository

## How It Works

1. **Fetch Repositories**: Retrieves all targets from your Snyk organization
2. **Filter Compatible Targets**: Only processes Git-based repositories (GitHub, GitLab, etc.)
3. **Generate AI-BOMs**: Creates AI Bill of Materials for each repository
4. **Search**: Looks for your keyword in the AI-BOM content
5. **Report**: Shows which repositories contain the specified component

## Supported Repository Types

- GitHub
- GitHub Enterprise
- GitLab
- Azure Repos
- Bitbucket Cloud

Container images and manual uploads are automatically skipped.

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone <repository-url>
cd ai-bom-scan

# Install in editable mode with uv
uv pip install -e .

# Or with pip
pip install -e .
```

### Making Changes

After making changes to `main.py`, the console command will immediately reflect your changes (thanks to editable install with `-e`).

## API Version

This tool uses Snyk AI-BOM API version `2025-07-22`. If you need to use a different API version, you can modify the default in the `SnykAIBomScanner` class.

## Troubleshooting

### Common Issues

**"Error: Please set SNYK_ORG_ID and SNYK_TOKEN environment variables"**
- Make sure both environment variables are set correctly
- Verify your token is valid and has the necessary permissions

**"Could not retrieve any targets"**
- Check that your organization has repositories connected
- Verify your token has access to the specified organization

### Debug Mode

Use `--debug` flag to see detailed information about:
- API requests and responses
- Job polling status
- Target processing details
- Keyword search results
