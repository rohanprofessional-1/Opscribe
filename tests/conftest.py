"""
Main pytest configuration for Opscribe tests.

This file provides shared fixtures and configuration for all tests.
"""

import pytest
import sys
from pathlib import Path

# Add the apps/api directory to the Python path so we can import the app
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root / "apps" / "api"))

# Now we can import from the app
from apps.api.ingestors.aws.detector import AWSDetector


@pytest.fixture
def aws_detector():
    """Create an AWS detector instance for testing"""
    return AWSDetector(region_name="us-east-1")
