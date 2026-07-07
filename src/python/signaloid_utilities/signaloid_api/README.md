# Signaloid API Utilities

The Signaloid C0-microSD comes pre-configured with the Signaloid SoC, a soft processor that supports a subset of Signaloid's technology for deterministic arithmetic on probability distributions, also referred to as Uncertainty Tracking (UT).  Signaloid offers an API endpoint for building applications that support UT, and target the Signaloid SoC. This module provides utilities for interacting with Signaloid's API to build your applications and download the binaries, which you can then flash to the Signaloid C0-microSD using the `C0_microSD_Toolkit.py`, located at the root of this repository

## Features

- Download microSD core binaries from Signaloid's API
- Build directly from GitHub repositories with a simple URL
- Support for multiple core versions (C0-microSD-XS, C0-microSD-XS+, C0-microSD-N, C0-microSD-N+)
- Configure repository settings including branch, commit, build directory, and more
- Progress tracking and verbose output
- Both command-line and programmatic usage
- Robust error handling

## Requirements

- Python 3.6+
- `requests` library
- Signaloid Cloud Developer Platform account and API key

## Installation

The module is part of the C0-microSD utilities package. No separate installation is needed if you have cloned the repository.

Make sure you have the required dependencies:
```bash
pip install requests
```

## Usage

### Command Line Interface

You can use the module directly from the command line. Make sure you're in the root directory of the project:

```bash
# Basic usage with repository ID
python -m src.python.signaloid_api.core_downloader --api-key YOUR_API_KEY --repo-id YOUR_REPO_ID

# Build directly from a GitHub repository URL
python -m src.python.signaloid_api.core_downloader --api-key YOUR_API_KEY --repo-url https://github.com/username/repository

# Specify a different core version
python -m src.python.signaloid_api.core_downloader --api-key YOUR_API_KEY --repo-id YOUR_REPO_ID --core C0-microSD-XS+

# Build from a specific branch
python -m src.python.signaloid_api.core_downloader --api-key YOUR_API_KEY --repo-id YOUR_REPO_ID --branch develop

# Specify output path
python -m src.python.signaloid_api.core_downloader --api-key YOUR_API_KEY --repo-id YOUR_REPO_ID \
    --output my_core.tar.gz

# Suppress progress messages
python -m src.python.signaloid_api.core_downloader --api-key YOUR_API_KEY --repo-id YOUR_REPO_ID --quiet

# Specify a different API endpoint
python -m src.python.signaloid_api.core_downloader --api-key YOUR_API_KEY --repo-id YOUR_REPO_ID \
    --base-url https://api.alternate-domain.com

# Specify a different build directory
python -m src.python.signaloid_api.core_downloader --api-key YOUR_API_KEY --repo-id YOUR_REPO_ID \
    --build-directory MY_SOURCE_DIRECTORY

# If Python can't find the module, add the current directory to PYTHONPATH:
PYTHONPATH=. python -m src.python.signaloid_api.core_downloader --api-key YOUR_API_KEY --repo-id YOUR_REPO_ID
```

#### Example with Output

Here's an example of building from a GitHub repository:

```bash
$ python -m src.python.signaloid_api.core_downloader --api-key YOUR_API_KEY --repo-url https://github.com/signaloid/Signaloid-C0-microSD-Demo-Calculator

Verifying GitHub repository: https://github.com/signaloid/Signaloid-C0-microSD-Demo-Calculator
Repository signaloid/Signaloid-C0-microSD-Demo-Calculator is valid and has a src directory
Creating Signaloid repository from GitHub URL: https://github.com/signaloid/Signaloid-C0-microSD-Demo-Calculator
Repository created with ID: rep_5c8104c6bb47468bbce9e0d1a83d2123

Using C0-microSD-N (default)

Creating build for repository rep_5c8104c6bb47468bbce9e0d1a83d2123 with C0-microSD-N...
Build created with ID: bld_ddff3fd873304eccaf68b7ce6f277123

Waiting for build to complete...
Build status: Initialising
Build status: Completed

Getting build outputs...
Build outputs retrieved

Build output:


Downloading binary...
Binary downloaded to: buildArtifacts.tar.gz
```

The downloaded `buildArtifacts.tar.gz` file contains the compiled binary and can be flashed to your C0-microSD device using the `C0_microSD_toolkit.py` script.

### Python API

You can also use the module programmatically in your Python code:

```python
from signaloid_api import download_core, update_repository, AVAILABLE_CORES
from pathlib import Path

# Basic usage with repository ID
output_file = download_core(
    api_key="YOUR_API_KEY",
    repo_id="YOUR_REPO_ID"  # Uses C0-microSD-N by default
)

# Using a GitHub repository URL
output_file = download_core(
    api_key="YOUR_API_KEY",
    repo_url="https://github.com/username/repository"  # Uses C0-microSD-N by default
)

# With all options
output_file = download_core(
    api_key="YOUR_API_KEY",
    repo_id="YOUR_REPO_ID",  # Either repo_id or repo_url must be provided
    # repo_url="https://github.com/username/repository",  # Alternative to repo_id
    core="C0-microSD-XS+",  # Core version (C0-microSD-XS, C0-microSD-XS+, C0-microSD-N, C0-microSD-N+)
    output_path=Path("output.tar.gz"),  # Custom output path
    base_url="https://api.signaloid.io",  # API endpoint (default: https://api.signaloid.io)
    verbose=True,  # Enable/disable progress messages
    branch="develop",  # Specific branch to build from
    build_directory="src"  # Specific directory where build sources are located
)

# Update repository configuration
update_repository(
    repo_id="YOUR_REPO_ID",
    headers={"Authorization": "YOUR_API_KEY"},
    base_url="https://api.signaloid.io",
    branch="main",              # Switch to a specific branch
    commit="abc123",           # Use a specific commit
    build_directory="src",     # Set build directory
    arguments="--flag value",  # Set build arguments
    core="cor_123...",        # Set core ID
    data_sources=[],          # Set data sources
    trace_variables=[]        # Set trace variables
)
```

## Choosing Between Repository ID and Repository URL

You have two options to identify your repository:

1. **Signaloid Repository ID**: Use this if you already have a repository set up in the Signaloid Cloud Developer Platform.
   - Format: `--repo-id YOUR_REPO_ID`
   - Example: `--repo-id rep_8a72b3f109e75c8d96ae4302ea7c5621`

2. **GitHub Repository URL**: Use this to directly build from a GitHub repository.
   - Format: `--repo-url https://github.com/username/repository`
   - Example: `--repo-url https://github.com/signaloid/Signaloid-C0-microSD-Demo-Calculator`
   - Requirements: 
     - Must either have a `src` directory in the root, or have specified the `--build-directory`
     - For private repositories only: You must connect your GitHub account in the Signaloid Cloud Developer Platform
     - Works with both public repositories and private repositories you have access to

You must provide either `--repo-id` or `--repo-url`, but not both.

## GitHub Repository Requirements

When using a GitHub repository URL:

1. The repository must have a `src` directory in the root
2. The `src` directory must contain a valid Signaloid C0-microSD application
3. The URL format should be: `https://github.com/username/repository`
4. For private repositories only: You must connect your GitHub account in the Signaloid Cloud Developer Platform

The tool will automatically:
1. Verify the repository exists and has a `src` directory
2. Connect the GitHub repository to the Signaloid platform
3. Build the application using the specified core
4. Download the resulting binary as `buildArtifacts.tar.gz` (unless you specify a different name)

## Available Core Versions

The following core versions are available for the C0-microSD:

- `C0-microSD-XS`: Extra small precision core
- `C0-microSD-XS+`: Extra small precision core with autocorrelation
- `C0-microSD-N`: Nano precision core (default)
- `C0-microSD-N+`: Nano precision core with autocorrelation

### Error Handling

The module provides detailed error messages in the format:
```
[Action]. Error: [API error message]
```

Common actions include:
- Repository update
- Build creation
- Build status check
- Build outputs retrieval
- Binary download

### Build Process

The build process follows these steps:
1. Updates repository configuration if a branch is specified
2. Creates a new build with the selected core
3. Monitors build status until completion
4. Retrieves and displays build outputs
5. Downloads the binary upon successful build

Progress messages are shown by default and can be disabled with `--quiet`.

## Repository Configuration

When using the Python API, you can configure various aspects of your repository using the `update_repository` function:

- `branch`: Switch to a different branch
- `commit`: Use a specific commit hash
- `build_directory`: Set the directory containing the build files
- `arguments`: Specify build arguments
- `core`: Set a specific core ID
- `data_sources`: Configure data sources for the build
- `trace_variables`: Set trace variables for the build

All parameters are optional, and you can update any combination of them in a single call.
