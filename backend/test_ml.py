"""Quick test for ML-based attack detector"""

from ml.attack_detector import detector

print("\n=== ML Attack Detector Test ===\n")

test_cases = [
    ("<script>alert('xss')</script>", "xss", "should detect"),
    ("1' OR '1'='1", "sqli", "should detect"),
    ("john@example.com", "normal", "should allow"),
    ("search_keyword", "normal", "should allow"),
]

for text, expected, description in test_cases:
    result = detector.predict(text)
    match = "✓" if result['label'] == expected else "✗"
    is_attack = "ATTACK" if result['is_attack'] else "NORMAL"
    
    print(f"{match} {description}")
    print(f"   Input: {text[:50]}")
    print(f"   Predicted: {result['label']} ({is_attack}, confidence: {result['confidence']})")
    print(f"   Expected: {expected}\n")

print("=== Test Complete ===\n")
