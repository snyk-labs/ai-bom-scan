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

### Command Line (after installation)

```bash
# Basic usage
ai-bom-scan "deepseek"

# Search for multiple terms with OR logic (comma-separated)
ai-bom-scan "deepseek,openai"

# Enable debug output
ai-bom-scan --debug "pytorch"

# Get help
ai-bom-scan --help
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
ai-bom-scan "deepseek"
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
ai-bom-scan "deepseek,openai,anthropic"
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
ai-bom-scan --debug "openai,claude"
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

### Project Structure

```
ai-bom-scan/
├── main.py           # Main application code
├── pyproject.toml    # Project configuration
├── uv.lock          # Dependency lock file
└── README.md        # This file
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
