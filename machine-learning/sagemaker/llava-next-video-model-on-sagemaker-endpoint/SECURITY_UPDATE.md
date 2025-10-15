# Security Update: Vulnerability Mitigations

## CVE-2025-4565: Protobuf Python Recursion Limit Vulnerability

### Summary
This update addresses a security vulnerability (CVE-2025-4565) in the protobuf library. The vulnerability affects projects using the Protobuf pure-Python backend to parse untrusted Protocol Buffers data containing recursive elements, which could lead to a denial of service by exceeding Python's recursion limit.

### Affected Components
- sagemaker-realtime-inference
- sagemaker-async-inference

### Updates Applied
- Updated protobuf from version 3.20.3 to version 4.25.8 in requirements.txt for both components

### Details
The vulnerability specifically impacts the pure-Python implementation of the protobuf-python backend, which is used by default with Bazel or pure-Python PyPi wheels, or when the PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION environment variable is set to "python".

### Severity
This is a potential Denial of Service vulnerability. Parsing nested protobuf data creates unbounded recursions that can be abused by an attacker.

### Reference
- Reporter: Alexis Challande, Trail of Bits Ecosystem Security Team
- CVE: CVE-2025-4565
- Safe versions: protobuf-python 4.25.8, 5.29.5, 6.31.1

## Transformers Regular Expression Denial of Service (ReDoS) Vulnerability

### Summary
This update addresses a security vulnerability in the huggingface/transformers library where versions prior to 4.53.0 are vulnerable to Regular Expression Denial of Service (ReDoS) in the AdamWeightDecay optimizer.

### Affected Components
- sagemaker-realtime-inference (previously using transformers 4.51.0)
- sagemaker-async-inference (previously using transformers 4.50.0)

### Updates Applied
- Updated transformers from version 4.51.0/4.50.0 to version 4.53.0 or later in requirements.txt for both components

### Details
The vulnerability arises from the _do_use_weight_decay method, which processes user-controlled regular expressions in the include_in_weight_decay and exclude_from_weight_decay lists. Malicious regular expressions can cause catastrophic backtracking during the re.search call, leading to 100% CPU utilization and a denial of service.

### Severity
This is a potential Denial of Service vulnerability. Attackers who can control the patterns in these lists could potentially cause the machine learning task to hang and render services unresponsive.

### Reference
- CVE: Not specified
- Safe versions: transformers 4.53.0 or later

### Date
Security updates applied: October 15, 2025