RULES = {
    'sql_injection': {
        'patterns': [
            r'\bunion\b\s+\bselect\b',
            r'\bor\b\s+1=1\b',
            r'\band\b\s+1=1\b',
            r'(--|#)',
            r'\binformation_schema\b',
            r'\bsleep\s*\(',
            r'\bbenchmark\s*\(',
            r'\bload_file\s*\(',
            r'\binto\s+outfile\b',
            r'\$ne\b',
        ],
        'score': 5,
    },
    'command_injection': {
        'patterns': [
            r';\s*(?:ls|cat|rm|whoami|chmod|chown|nc|curl|wget|bash|sh)\b',
            r'&&\s*(?:ls|cat|rm|whoami|chmod|chown|nc|curl|wget|bash|sh)\b',
            r'\|\|\s*(?:ls|cat|rm|whoami|chmod|chown|nc|curl|wget|bash|sh)\b',
            r'\|\s*(?:ls|cat|rm|whoami|chmod|chown|nc|curl|wget|bash|sh)\b',
            r'\$\(',
            r'`[^`]+`',
        ],
        'score': 5,
    },
    'ssrf': {
        'patterns': [
            r'\bhttps?://(?:127(?:\.\d{1,3}){3}|localhost|169\.254\.169\.254|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2[0-9]|3[0-1])\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3})\b',
            r'\bfile://',
            r'\b127(?:\.\d{1,3}){3}\b',
            r'\blocalhost\b',
            r'\b169\.254\.169\.254\b',
        ],
        'score': 5,
    },
    'path_traversal': {
        'patterns': [r'\.\./', r'\.\.\\', r'%2e%2e%2f', r'%2e%2e\\'],
        'score': 5,
    },
    'xss': {
        'patterns': [
            r'<script\b',
            r'javascript:',
            r'onerror\s*=',
            r'onload\s*=',
            r'document\.cookie',
            r'<iframe\b',
            r'<svg\b',
            r'alert\s*\(',
        ],
        'score': 4,
    },
}
