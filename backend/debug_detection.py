#!/usr/bin/env python3
"""
Debug detection - see what patterns are triggering
"""

import sys
sys.path.insert(0, 'd:\\INTRUSION - X\\GOOD API\\api-gateway-hackathon\\backend')

from security.detector import detect_attacks, _normalize_text
from fastapi import Request
from unittest.mock import Mock
import urllib.parse

# Test patterns
test_cases = [
    ("' OR '1'='1", "SQLi with quotes"),
    ("OR 1=1", "Simple OR 1=1"),
    ("<script>alert(1)</script>", "XSS script"),
    ("<img src=x onerror=alert(1)>", "XSS onerror"),
    ("normal request", "Normal"),
]

print("\n" + "="*70)
print("PATTERN DETECTION DEBUG")
print("="*70 + "\n")

for payload, description in test_cases:
    print(f"Testing: {description}")
    print(f"Payload: {payload}")
    
    # Normalize to see what the detector sees
    normalized = _normalize_text(payload)
    print(f"Normalized: {normalized}")
    
    # Create mock request
    mock_request = Mock(spec=Request)
    mock_request.url.path = "/api/user"
    mock_request.url.query = urllib.parse.urlencode({'id': payload})
    mock_request.headers = {}
    mock_request.method = "GET"
    
    # Run detection
    result = detect_attacks(mock_request, b'')
    print(f"Detection result:")
    print(f"  Score: {result['score']}")
    print(f"  Reasons: {result['reasons']}")
    print()

