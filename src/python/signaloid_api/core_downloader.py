#!/usr/bin/env python3

# Copyright (c) 2025, Signaloid.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import requests
import json
import time
import argparse
import sys
import re
from typing import Dict, Optional, Tuple
from pathlib import Path

# Available C0-microSD cores configuration
AVAILABLE_CORES: Dict[str, str] = {
    "C0-microSD-XS": "cor_808bbbb9932c5d29a58370a1ec9a859f",
    "C0-microSD-XS+": "cor_3d8dfc5d4f305e16b867716fe6aba1e9",
    "C0-microSD-N": "cor_271d544c73a8544d9026252652342972",
    "C0-microSD-N+": "cor_c1cde893b0d75bb6a8941e9caf90f2a6"
}


class SignaloidAPIError(Exception):
    """Custom exception for Signaloid API errors."""
    pass


def _handle_api_error(e: requests.exceptions.HTTPError, action: str) -> None:
    """Helper function to handle API errors consistently.

    Args:
        e: The HTTP error from the request
        action: The action that was being performed when the error occurred

    Raises:
        SignaloidAPIError: With formatted error message
    """
    try:
        error_details = e.response.json()
        print(f"\nAction: {action}")
        print(f"Status Code: {e.response.status_code}")
        print(f"Headers: {dict(e.response.headers)}")
        print(f"Response Body: {json.dumps(error_details, indent=2)}")
        error_msg = f"{action} failed: {error_details}"
        raise SignaloidAPIError(error_msg) from e
    except json.JSONDecodeError:
        print(f"\nAction: {action}")
        print(f"Status Code: {e.response.status_code}")
        print(f"Headers: {dict(e.response.headers)}")
        print(f"Response Body: {e.response.text}")
        error_msg = f"{action} failed: {e.response.text}"
        raise SignaloidAPIError(error_msg) from e


def create_build_from_repository(
        repo_id: str,
        core_id: str,
        headers: dict,
        base_url: str,
        branch: Optional[str] = None) -> str:
    """Create a new build from repository.

    Args:
        repo_id: Repository ID to build from
        core_id: Core ID to use for the build
        headers: Request headers including authentication
        base_url: Base URL for the Signaloid API
        branch: Optional branch name to build from
               (default: repository default)

    Returns:
        str: Build ID of the created build

    Raises:
        requests.exceptions.HTTPError: If the API request fails
    """
    url = f"{base_url}/repositories/{repo_id}/builds"

    build_request = {
        "CoreID": core_id,
        "TraceVariables": [],
        "DataSources": [],
        "Arguments": ""
    }

    if branch:
        build_request["Branch"] = branch

    response = requests.post(url, headers=headers, json=build_request)
    response.raise_for_status()
    return response.json()["BuildID"]


def check_build_status(build_id: str, headers: dict, base_url: str) -> str:
    """Check the status of a build.

    Args:
        build_id: ID of the build to check
        headers: Request headers including authentication
        base_url: Base URL for the Signaloid API

    Returns:
        str: Current status of the build

    Raises:
        requests.exceptions.HTTPError: If the API request fails
    """
    url = f"{base_url}/builds/{build_id}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json().get("Status", "Unknown")


def get_binary_url(build_id: str, headers: dict, base_url: str) -> str:
    """Get pre-signed URL for the binary.

    Args:
        build_id: ID of the build to download
        headers: Request headers including authentication
        base_url: Base URL for the Signaloid API

    Returns:
        str: Pre-signed URL for downloading the binary

    Raises:
        requests.exceptions.HTTPError: If the API request fails
    """
    url = f"{base_url}/builds/{build_id}/binary"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()["url"]


def get_build_outputs(build_id: str, headers: dict, base_url: str) -> str:
    """Get the build output URL.

    Args:
        build_id: ID of the build to get outputs for
        headers: Request headers including authentication
        base_url: Base URL for the Signaloid API

    Returns:
        str: Pre-signed S3 URL for downloading the build output

    Raises:
        requests.exceptions.HTTPError: If the API request fails
        SignaloidAPIError: If no build output URL is found
    """
    url = f"{base_url}/builds/{build_id}/outputs"
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    build_url = response.json().get("Build")
    if not build_url:
        raise SignaloidAPIError("No build output URL found in response")

    return build_url


def download_binary(url: str, output_path: Optional[Path] = None) -> Path:
    """Download the binary using pre-signed URL.

    Args:
        url: Pre-signed URL for downloading the binary
        output_path: Optional path to save the binary to

    Returns:
        Path: Path to the downloaded binary

    Raises:
        requests.exceptions.HTTPError: If the download fails
    """
    response = requests.get(url)
    response.raise_for_status()

    if output_path is None:
        output_path = Path("buildArtifacts.tar.gz")

    output_path.write_bytes(response.content)
    return output_path


def update_repository(
        repo_id: str,
        headers: dict,
        base_url: str,
        *,
        branch: Optional[str] = None,
        commit: Optional[str] = None,
        build_directory: Optional[str] = None,
        arguments: Optional[str] = None,
        core: Optional[str] = None,
        data_sources: Optional[list] = None,
        trace_variables: Optional[list] = None) -> None:
    """Update the repository's configuration.

    Args:
        repo_id: Repository ID to update
        headers: Request headers including authentication
        base_url: Base URL for the Signaloid API
        branch: Optional branch name to switch to
        commit: Optional commit hash to use
        build_directory: Optional build directory path
        arguments: Optional build arguments
        core: Optional core ID
        data_sources: Optional list of data sources
        trace_variables: Optional list of trace variables

    Raises:
        requests.exceptions.HTTPError: If the API request fails
    """
    url = f"{base_url}/repositories/{repo_id}"

    update_request = {}
    if branch is not None:
        update_request["Branch"] = branch
    if commit is not None:
        update_request["Commit"] = commit
    if build_directory is not None:
        update_request["BuildDirectory"] = build_directory
    if arguments is not None:
        update_request["Arguments"] = arguments
    if core is not None:
        update_request["Core"] = core
    if data_sources is not None:
        update_request["DataSources"] = data_sources
    if trace_variables is not None:
        update_request["TraceVariables"] = trace_variables

    if not update_request:
        return  # Nothing to update

    response = requests.patch(url, headers=headers, json=update_request)
    response.raise_for_status()


def verify_github_repo(
        repo_url: str,
        base_url: str,
        headers: dict,
        verbose: bool = True) -> Tuple[bool, str]:
    """
    Verify if a GitHub repository exists and has a src directory.

    Args:
        repo_url: GitHub repository URL
        base_url: Base URL for the Signaloid API
        headers: Request headers including authentication
        verbose: Whether to print progress messages

    Returns:
        Tuple containing:
            - success (bool): Whether the verification was successful
            - message (str): Success or error message
            
    Raises:
        SignaloidAPIError: If the API request fails
    """
    if verbose:
        print(f"Verifying GitHub repository: {repo_url}")

    # Extract username and repo name from the URL
    match = re.search(r'github\.com/([^/]+)/([^/]+)', repo_url)
    if not match:
        return (
            False,
            "Invalid GitHub URL format. "
            "Expected: https://github.com/username/reponame")

    username, repo_name = match.groups()

    # Remove .git suffix if present
    repo_name = repo_name.replace('.git', '')

    # Call the GitHub proxy API to verify the repository exists
    proxy_url = f"{base_url}/proxy/github/repos/{username}/{repo_name}"

    try:
        response = requests.get(proxy_url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        _handle_api_error(e, "Repository verification")
        return False, ""  # This line will never be reached due to the raise in _handle_api_error
    
    # Check if repository has a src directory
    contents_url = f"{base_url}/proxy/github/repos/"
    contents_url += f"{username}/{repo_name}/contents"

    try:
        response = requests.get(contents_url, headers=headers)
        response.raise_for_status()

        contents = response.json()
        has_src = any(item.get('name') == 'src' and item.get('type') == 'dir'
                      for item in contents)

        if not has_src:
            return (False,
                    "Repository does not have a "
                    "'src' directory in the root")

    except requests.exceptions.HTTPError as e:
        _handle_api_error(e, "Repository contents verification")
        return False, ""  # This line will never be reached due to the raise in _handle_api_error
    
    return True, f"Repository {username}/{repo_name} is valid and has a src directory"


def connect_repository_from_github(
        repo_url: str,
        headers: dict,
        base_url: str,
        branch: str = "main",
        verbose: bool = True) -> str:
    """
    Connect a GitHub repository to the Signaloid Cloud Developer Platform.

    Args:
        repo_url: GitHub repository URL
        headers: Request headers including authentication
        base_url: Base URL for the Signaloid API
        branch: Branch to use (default: main)
        verbose: Whether to print progress messages

    Returns:
        str: Signaloid repository ID of the connected repository

    Raises:
        SignaloidAPIError: If the connection fails
    """
    if verbose:
        print("Connecting GitHub repository to "
              f"Signaloid Cloud Developer Platform: {repo_url}")

    url = f"{base_url}/repositories"

    repo_data = {
        "RemoteURL": repo_url,
        "Commit": "HEAD",
        "BuildDirectory": "src",
        "Arguments": "",
        "Branch": branch or "main"
    }

    try:
        response = requests.post(url, headers=headers, json=repo_data)
        response.raise_for_status()

        repo_id = response.json().get("RepositoryID")
        if not repo_id:
            raise SignaloidAPIError(
                "Repository connected but no Signaloid repository ID returned")

        if verbose:
            print(f"Repository connected with Signaloid ID: {repo_id}")

        return repo_id

    except requests.exceptions.HTTPError as e:
        _handle_api_error(e, "Repository connection")


def download_core(
        api_key: str,
        repo_id: Optional[str] = None,
        core: str = 'C0-microSD-N',
        output_path: Optional[Path] = None,
        base_url: str = "https://api.signaloid.io",
        verbose: bool = True,
        branch: Optional[str] = None,
        repo_url: Optional[str] = None) -> Path:
    """Download a microSD core binary from Signaloid's API.

    Args:
        api_key: Signaloid API key
        repo_id: Signaloid repository ID to build from
                 (required if repo_url not provided)
        core: Core version to use (C0-microSD-XS, C0-microSD-XS+,
              C0-microSD-N, C0-microSD-N+)
        output_path: Optional path to save the binary to
        base_url: Base URL for the Signaloid API
                 (default: https://api.signaloid.io)
        verbose: Whether to print progress messages
        branch: Optional branch name to build from
               (default: repository default)
        repo_url: GitHub repository URL (alternative to repo_id)

    Returns:
        Path: Path to the downloaded binary

    Raises:
        SignaloidAPIError: If any step of the process fails
        ValueError: If an invalid core version is specified or if neither
                   repo_id nor repo_url is provided
    """
    if repo_id is None and repo_url is None:
        raise ValueError("Either repo_id or repo_url must be provided")

    # If repo_url is provided but repo_id is not, connect a repository
    # from the URL
    if repo_id is None and repo_url is not None:
        headers = {
            "Authorization": api_key,
            "Content-Type": "application/json"
        }

        # First verify the GitHub repository
        is_valid, message = verify_github_repo(
            repo_url, base_url, headers, verbose)
        if not is_valid:
            raise ValueError(f"Invalid GitHub repository: {message}")

        if verbose:
            print(message)

        # Connect the repository to Signaloid
        repo_id = connect_repository_from_github(
            repo_url, headers, base_url, branch, verbose)

    if core not in AVAILABLE_CORES:
        core_list = ', '.join(AVAILABLE_CORES.keys())
        raise ValueError(
            f"Invalid core version. Must be one of: {core_list}")

    if verbose:
        is_default = " (default)" if core == 'C0-microSD-N' else ""
        print(f"\nUsing {core}{is_default}\n")

    core_id = AVAILABLE_CORES[core]
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json"
    }

    try:
        # Step 1: Update repository branch if specified
        if branch and repo_url is None:
            # Only update branch if using repo_id directly
            if verbose:
                repo_msg = f"Updating repository {repo_id}"
                branch_msg = f"to branch {branch}"
                print(f"{repo_msg} {branch_msg}...")
            try:
                update_repository(repo_id, headers, base_url, branch=branch)
                if verbose:
                    print("Repository branch updated\n")
            except requests.exceptions.HTTPError as e:
                _handle_api_error(e, "Repository update")

        # Step 2: Create build
        if verbose:
            branch_info = f" from branch {branch}" if branch else ""
            print(f"Creating build for repository {repo_id} "
                  f"with {core}{branch_info}...")
        try:
            build_id = create_build_from_repository(
                repo_id,
                core_id,
                headers,
                base_url,
                branch if repo_url else None)
            if verbose:
                print(f"Build created with ID: {build_id}\n")
        except requests.exceptions.HTTPError as e:
            _handle_api_error(e, "Build creation")

        # Step 3: Wait for build completion
        if verbose:
            print("Waiting for build to complete...")
        last_status = None
        while True:
            try:
                status = check_build_status(build_id, headers, base_url)
            except requests.exceptions.HTTPError as e:
                _handle_api_error(e, "Build status check")

            # Only print status if it changed
            if verbose and status != last_status:
                print(f"Build status: {status}")
                last_status = status

            if status == "Completed":
                print("")  # Add extra newline after completion
                break
            elif status in ["Stopped", "Cancelled", "Failed"]:
                try:
                    error_out = get_build_outputs(build_id, headers, base_url)
                    print("\nBuild output:")
                    print(requests.get(error_out).text)
                except requests.exceptions.HTTPError as e:
                    _handle_api_error(e, "Build outputs retrieval")
                except Exception:
                    pass
                raise SignaloidAPIError(
                    f"Build execution: Build failed with status {status}")

            time.sleep(2)

        # Step 4: Get and display build outputs
        if verbose:
            print("Getting build outputs...")
        try:
            output_url = get_build_outputs(build_id, headers, base_url)
        except requests.exceptions.HTTPError as e:
            _handle_api_error(e, "Build outputs retrieval")

        if verbose:
            print("Build outputs retrieved")
            print("\nBuild output:")
            output_content = requests.get(output_url).text
            print(output_content)

        # Step 5: Download binary using binary endpoint
        if verbose:
            print("\nDownloading binary...")
        try:
            binary_url = get_binary_url(build_id, headers, base_url)
            output_file = download_binary(binary_url, output_path)
        except requests.exceptions.HTTPError as e:
            _handle_api_error(e, "Binary download")

        if verbose:
            print(f"Binary downloaded to: {output_file}\n")

        return output_file

    except requests.exceptions.HTTPError as e:
        _handle_api_error(e, "Core download")
    except Exception as e:
        raise SignaloidAPIError(str(e)) from e


def main():
    """Command-line interface for downloading microSD core binaries."""
    description = 'Build and download Signaloid microSD core binary.'
    parser = argparse.ArgumentParser(description=description)

    # Create a mutually exclusive group for repo_id and repo_url
    repo_group = parser.add_mutually_exclusive_group(required=True)
    repo_group.add_argument(
        '--repo-id',
        help='Your repository ID'
    )
    repo_group.add_argument(
        '--repo-url',
        help='GitHub repository URL (e.g., https://github.com/username/repo)'
    )

    parser.add_argument(
        '--api-key',
        required=True,
        help='Your Signaloid API key'
    )
    parser.add_argument(
        '--core',
        choices=AVAILABLE_CORES.keys(),
        default='C0-microSD-N',
        help='MicroSD core version (default: C0-microSD-N for nano precision)'
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='Output path for the binary'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress progress messages'
    )
    parser.add_argument(
        '--branch',
        help='Branch name to build from (default: repository default)'
    )
    parser.add_argument(
        '--base-url',
        default='https://api.signaloid.io',
        help='Base URL for the Signaloid API '
        '(default: https://api.signaloid.io)'
    )

    args = parser.parse_args()

    try:
        download_core(
            args.api_key,
            args.repo_id,
            args.core,
            args.output,
            base_url=args.base_url,
            verbose=not args.quiet,
            branch=args.branch,
            repo_url=args.repo_url
        )
    except (SignaloidAPIError, ValueError) as e:
        print(f"{str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
