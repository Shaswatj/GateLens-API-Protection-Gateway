"""Labeled training dataset for ML attack detector"""

TRAINING_DATA = [
    # XSS attacks (7 samples)
    {"input": "<script>alert('xss')</script>", "label": "xss"},
    {"input": "'\"><script>alert(1)</script>", "label": "xss"},
    {"input": "javascript:alert(1)", "label": "xss"},
    {"input": "<img src=x onerror=alert(1)>", "label": "xss"},
    {"input": "<svg onload=alert(1)>", "label": "xss"},
    {"input": "<body onload=alert(1)>", "label": "xss"},
    {"input": "eval(String.fromCharCode(97,108,101,114,116))", "label": "xss"},
    
    # SQL Injection (7 samples)
    {"input": "1' OR '1'='1", "label": "sqli"},
    {"input": "1 UNION SELECT password FROM users", "label": "sqli"},
    {"input": "'; DROP TABLE users; --", "label": "sqli"},
    {"input": "admin' --", "label": "sqli"},
    {"input": "1' AND 1=1 UNION SELECT NULL, NULL", "label": "sqli"},
    {"input": "' OR 1=1 /*", "label": "sqli"},
    {"input": "1; DELETE FROM users WHERE 1=1", "label": "sqli"},
    
    # Normal requests (8 samples)
    {"input": "john.doe@example.com", "label": "normal"},
    {"input": "search_query_keyword", "label": "normal"},
    {"input": "user123", "label": "normal"},
    {"input": "Hello World", "label": "normal"},
    {"input": "password123", "label": "normal"},
    {"input": "2024-01-15", "label": "normal"},
    {"input": "item_id_567", "label": "normal"},
    {"input": "api_request_data", "label": "normal"},
]
