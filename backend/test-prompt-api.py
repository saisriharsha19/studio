import asyncio
import aiohttp
import time
import random
import statistics
from collections import defaultdict

# CONFIGURATION
URL = "http://localhost:5000/generate-initial-prompt"
TOTAL_USERS = 200
DELAY_BETWEEN_USERS = 0.05
MAX_CONCURRENT_REQUESTS = 100

# Store results
results = []
errors = defaultdict(int)

def generate_payload(user_id: int):
    return {
        "userNeeds": f"Generate a prompt for {random.choice(['marketing', 'education', 'robotics'])} use case by user-{user_id}"
    }

semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

async def simulate_user(user_id: int, session: aiohttp.ClientSession):
    async with semaphore:
        payload = generate_payload(user_id)
        try:
            start = time.time()
            async with session.post(URL, json=payload) as response:
                duration = time.time() - start
                status = response.status
                results.append((status, duration))
                print(f"[User {user_id}] Status: {status}, Time: {duration:.2f}s")
                if status != 200:
                    errors[status] += 1
        except Exception as e:
            print(f"[User {user_id}] Exception: {e}")
            results.append(("exception", 0))
            errors["exception"] += 1

async def main():
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(TOTAL_USERS):
            tasks.append(simulate_user(i, session))
            await asyncio.sleep(DELAY_BETWEEN_USERS)
        await asyncio.gather(*tasks)

    # === Summary ===
    durations = [d for s, d in results if isinstance(d, float)]
    total = len(results)
    success = sum(1 for s, _ in results if s == 200)
    failure = total - success

    print("\n===== LOAD TEST SUMMARY =====")
    print(f"Total Requests       : {total}")
    print(f"Success (200)        : {success}")
    print(f"Failures             : {failure}")
    if durations:
        print(f"Min Latency (s)      : {min(durations):.2f}")
        print(f"Max Latency (s)      : {max(durations):.2f}")
        print(f"Avg Latency (s)      : {statistics.mean(durations):.2f}")
        print(f"P95 Latency (s)      : {statistics.quantiles(durations, n=100)[94]:.2f}")
    else:
        print("No successful responses to compute latency stats.")

    print("\nError Breakdown:")
    for code, count in errors.items():
        print(f"  {code} : {count} errors")

if __name__ == "__main__":
    asyncio.run(main())
