# Advanced Asynchronous Stress Testing Tool

A robust and feature-rich **Asynchronous Stress Testing Tool** for evaluating web application performance under high load. Built with Python, this tool efficiently simulates high-volume concurrent HTTP requests, making it ideal for load testing and server bottleneck analysis.

---

## Features

- **Asynchronous Design**: Leverages `asyncio` and `aiohttp` for high scalability and efficiency.
- **Customizable Load Parameters**:
  - Concurrent connections
  - Total requests
  - Request timeout
  - HTTP method (`GET` or `POST`)
  - Data payload for POST requests
- **Proxy Support**:
  - Rotate proxies for each request.
  - Validate proxies asynchronously before use.
- **Retry Mechanism**: Uses exponential backoff for handling transient network issues.
- **User-Agent Rotation**: Simulates diverse clients by rotating through user-agent strings.
- **Comprehensive Logging**: Logs test progress, request statuses, errors, and metrics.
- **Detailed Reporting**:
  - Status code distribution
  - Error breakdown
  - Latency statistics (average, minimum, maximum, and percentiles: P50, P90, P99)
  - Requests per second
- **Configuration Options**:
  - Command-line arguments
  - JSON configuration file

---

## How to Run

Step 1: Install Dependencies

Ensure Python 3.7+ is installed. Install required libraries with:

pip install aiohttp tenacity



Step 2: Using the Program

Run the program with the following command:

```bash
python stress_test.py https://example.com -t 100 -r 100


| Option             | Description                                   | Default          |
|--------------------|-----------------------------------------------|------------------|
| `-t`, `--threads`  | Number of concurrent connections.             | `100`            |
| `-r`, `--requests` | Number of requests per thread.                | `1000`           |
| `--timeout`        | Request timeout in seconds.                   | `5`              |
| `--method`         | HTTP method to use (`GET` or `POST`).         | `GET`            |
| `--data`           | Data payload for POST requests (as a string). | `""`             |
| `--proxies`        | List of proxies (`http://proxy:port`) to use. | `[]`             |
| `--validate-proxies`| Validate proxies before testing.             | `False`          |
| `--log-file`       | Path to the log file.                         | `stress_test.log`|
| `--config`         | Path to a JSON configuration file.            | `None`           |
```bash
````
