import argparse
import asyncio
import aiohttp
import time
import logging
import random
import json
from collections import defaultdict
from aiohttp import ClientSession, ClientConnectorError
from typing import List, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# User-Agent list for request headers rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15"
]

def parse_args():
    parser = argparse.ArgumentParser(description="Advanced Asynchronous Stress Testing Tool")
    parser.add_argument("url", help="Target URL")
    parser.add_argument("-t", "--threads", type=int, default=100, help="Number of concurrent connections")
    parser.add_argument("-r", "--requests", type=int, default=1000, help="Requests per thread")
    parser.add_argument("--timeout", type=int, default=5, help="Request timeout in seconds")
    parser.add_argument("--method", choices=["GET", "POST"], default="GET", help="HTTP method")
    parser.add_argument("--data", type=str, default="", help="Data for POST requests")
    parser.add_argument("--proxies", type=str, nargs='*', default=[], help="List of proxies (format: http://proxy:port)")
    parser.add_argument("--log-file", type=str, default="stress_test.log", help="Log file path")
    parser.add_argument("--config", type=str, help="Path to JSON configuration file")
    parser.add_argument("--validate-proxies", action='store_true', help="Validate proxies before testing")
    return parser.parse_args()

def load_config(config_path: str) -> dict:
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except Exception as e:
        logging.error(f"Failed to load configuration file: {e}")
        return {}

def setup_logging(log_file: str):
    logging.basicConfig(
        filename=log_file,
        filemode='w',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(message)s')
    console.setFormatter(formatter)
    logging.getLogger().addHandler(console)

class StressTester:
    def __init__(self, url: str, total_requests: int, concurrency: int, timeout: int,
                 method: str, data: str, proxies: List[str], validate_proxies: bool = False):
        self.url = url
        self.total_requests = total_requests
        self.concurrency = concurrency
        self.timeout = timeout
        self.method = method.upper()
        self.data = data
        self.proxies = proxies
        self.validate_proxies = validate_proxies
        self.stats = {
            'status_codes': defaultdict(int),
            'errors': defaultdict(int)
        }
        self.latencies = []
        self.lock = asyncio.Lock()

    async def validate_proxy(self, session: ClientSession, proxy: str) -> bool:
        test_url = "http://httpbin.org/ip"
        try:
            async with session.get(test_url, proxy=proxy, timeout=10) as response:
                if response.status == 200:
                    logging.info(f"Proxy {proxy} is valid.")
                    return True
                else:
                    logging.warning(f"Proxy {proxy} returned status {response.status}.")
                    return False
        except Exception as e:
            logging.warning(f"Proxy {proxy} failed validation: {e}")
            return False

    async def validate_proxies_async(self) -> List[str]:
        valid_proxies = []
        connector = aiohttp.TCPConnector(limit=100)
        async with ClientSession(connector=connector) as session:
            tasks = [self.validate_proxy(session, proxy) for proxy in self.proxies]
            results = await asyncio.gather(*tasks)
            for proxy, is_valid in zip(self.proxies, results):
                if is_valid:
                    valid_proxies.append(proxy)
        self.proxies = valid_proxies
        if not self.proxies:
            logging.warning("No valid proxies available after validation.")
        return valid_proxies

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10),
           retry=retry_if_exception_type(aiohttp.ClientError))
    async def send_request(self, session: ClientSession):
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        proxy = random.choice(self.proxies) if self.proxies else None
        proxy_url = proxy if proxy else None
        start_time = time.time()
        try:
            async with session.request(
                self.method, self.url, headers=headers,
                data=self.data if self.method == "POST" else None,
                timeout=self.timeout,
                proxy=proxy_url
            ) as response:
                latency = time.time() - start_time
                async with self.lock:
                    self.latencies.append(latency)
                    self.stats['status_codes'][response.status] += 1
        except asyncio.TimeoutError:
            async with self.lock:
                self.stats['errors']['Timeout'] += 1
        except ClientConnectorError as e:
            async with self.lock:
                self.stats['errors'][str(e)] += 1
        except Exception as e:
            async with self.lock:
                self.stats['errors'][str(e)] += 1

    async def run(self):
        connector = aiohttp.TCPConnector(limit=self.concurrency)
        async with ClientSession(connector=connector) as session:
            if self.validate_proxies and self.proxies:
                await self.validate_proxies_async()

            tasks = []
            sem = asyncio.Semaphore(self.concurrency)

            async def sem_task():
                async with sem:
                    await self.send_request(session)

            for _ in range(self.total_requests):
                tasks.append(asyncio.create_task(sem_task()))

            await asyncio.gather(*tasks, return_exceptions=True)

    def report(self, duration: float):
        logging.info("\n--- Stress Test Report ---")
        logging.info(f"Total time: {duration:.2f} seconds")
        logging.info(f"Total requests: {self.total_requests}")
        successful = sum(self.stats['status_codes'].values())
        failed = self.total_requests - successful
        logging.info(f"Successful requests: {successful}")
        logging.info(f"Failed requests: {failed}")
        logging.info(f"Requests per second: {self.total_requests / duration:.2f}")
        if self.latencies:
            avg_latency = sum(self.latencies) / len(self.latencies)
            min_latency = min(self.latencies)
            max_latency = max(self.latencies)
            p50 = self._percentile(50)
            p90 = self._percentile(90)
            p99 = self._percentile(99)
            logging.info(f"Latency (s): Avg={avg_latency:.4f}, Min={min_latency:.4f}, Max={max_latency:.4f}")
            logging.info(f"Latency Percentiles (s): P50={p50:.4f}, P90={p90:.4f}, P99={p99:.4f}")
        logging.info("Status Codes:")
        for code, count in sorted(self.stats['status_codes'].items()):
            logging.info(f"  {code}: {count}")
        if self.stats['errors']:
            logging.info("Errors:")
            for error, count in sorted(self.stats['errors'].items(), key=lambda x: x[1], reverse=True):
                logging.info(f"  {error}: {count}")

    def _percentile(self, percentile: float) -> float:
        if not self.latencies:
            return 0.0
        sorted_latencies = sorted(self.latencies)
        index = int(len(sorted_latencies) * percentile / 100)
        return sorted_latencies[index] if index < len(sorted_latencies) else sorted_latencies[-1]

def main():
    args = parse_args()


    config = {}
    if args.config:
        config = load_config(args.config)


    url = args.url or config.get("url")
    threads = args.threads or config.get("threads", 100)
    requests_per_thread = args.requests or config.get("requests", 1000)
    timeout = args.timeout or config.get("timeout", 5)
    method = args.method or config.get("method", "GET")
    data = args.data or config.get("data", "")
    proxies = args.proxies or config.get("proxies", [])
    log_file = args.log_file or config.get("log_file", "stress_test.log")
    validate_proxies = args.validate_proxies or config.get("validate_proxies", False)

    if not url:
        logging.error("Target URL must be specified either as a command-line argument or in the config file.")
        return

    setup_logging(log_file)

    # Correctly calculate total_requests
    total_requests = threads * requests_per_thread

    tester = StressTester(
        url=url,
        total_requests=total_requests,
        concurrency=threads,
        timeout=timeout,
        method=method,
        data=data,
        proxies=proxies,
        validate_proxies=validate_proxies
    )

    start_time = time.time()
    logging.info("Starting stress test...")
    asyncio.run(tester.run())
    end_time = time.time()
    tester.report(end_time - start_time)

if __name__ == "__main__":
    main()
