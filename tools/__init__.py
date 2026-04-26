import re


def scan_injection_patterns(context: str) -> str:
    findings = []
    if re.search(r"'\s*(OR|AND)\s*'?\d", context, re.IGNORECASE):
        findings.append("Possible SQL injection: boolean-based pattern detected")
    if re.search(r";\s*(DROP|DELETE|INSERT|UPDATE)\s", context, re.IGNORECASE):
        findings.append("Possible SQL injection: stacked query pattern detected")
    if re.search(r"\$\(|`[^`]+`|\|\s*\w", context):
        findings.append("Possible command injection: shell expansion pattern detected")
    return "; ".join(findings) if findings else "No injection patterns detected"


def check_parameterised_queries(context: str) -> str:
    if re.search(r"(f['\"].*\{.*\}.*['\"]|%\s*\(?\w+\)?\s*%s|\"[^\"]*\"\s*\+)", context):
        return "String interpolation detected in query context — parameterisation not confirmed"
    return "No unsafe query construction detected"


def check_auth_headers(context: str) -> str:
    findings = []
    if re.search(r"(no auth|without auth|skip auth|bypass auth)", context, re.IGNORECASE):
        findings.append("Auth bypass language detected")
    if re.search(r"(token|session|cookie)\s*=\s*['\"]?\w{0,8}['\"]?", context, re.IGNORECASE):
        findings.append("Weak or hardcoded credential pattern detected")
    return "; ".join(findings) if findings else "No auth anomalies detected"


def scan_xss_patterns(context: str) -> str:
    findings = []
    if re.search(r"<script|javascript:|onerror=|onload=", context, re.IGNORECASE):
        findings.append("XSS payload pattern detected in context")
    if re.search(r"(innerHTML|document\.write|eval\()", context, re.IGNORECASE):
        findings.append("Dangerous DOM manipulation method referenced")
    return "; ".join(findings) if findings else "No XSS patterns detected"
