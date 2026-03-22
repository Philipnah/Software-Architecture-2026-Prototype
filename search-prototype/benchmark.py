import time
import json
import urllib.request
import urllib.parse
from datetime import datetime

BASE_URL = "http://localhost:8000/search"
ENGINES = ["postgres", "elasticsearch", "elasticsearch_enriched"]
RESULTS_FILE = "benchmark_results.txt"
CSV_FILE = "benchmark_results.csv"

TEST_CASES = [
    {"q": "", "genre": "", "filters": []},
    {"q": "zelda", "genre": "", "filters": []},
    {"q": "", "genre": "RPG", "filters": []},
    {"q": "mario", "genre": "platformer", "filters": []},
]

REQUEST_COUNTS = [1, 5, 10, 25, 50, 100, 500]


def build_url(engine: str, params: dict) -> str:
    query = {"engine": engine, **params}
    filters = query.pop("filters", [])
    encoded = urllib.parse.urlencode(query)
    if filters:
        encoded += "&" + "&".join(f"filters={urllib.parse.quote(f)}" for f in filters)
    return f"{BASE_URL}?{encoded}"


def send_request(url: str) -> float:
    start = time.perf_counter()
    with urllib.request.urlopen(url) as response:
        response.read()
    return time.perf_counter() - start


def fmt(val: float) -> str:
    return f"{val:.1f}".replace(".", ",")


def run_benchmark() -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [f"Benchmark run: {timestamp}", "=" * 60]

    # results[case_label][n][engine] = total_ms
    results = {}

    for params in TEST_CASES:
        case_label = f"q={params['q']!r} genre={params['genre']!r}"
        results[case_label] = {}
        lines.append(f"\n{case_label}")
        lines.append("-" * 60)
        print(f"\n{case_label}")

        for n in REQUEST_COUNTS:
            results[case_label][n] = {}
            print(f"  {n} requests:")

            for engine in ENGINES:
                url = build_url(engine, dict(params))
                times = []

                for _ in range(n):
                    try:
                        times.append(send_request(url))
                    except Exception as e:
                        print(f"    ERROR [{engine}]: {e}")

                if times:
                    total = sum(times)
                    results[case_label][n][engine] = total * 1000
                    line = f"    {engine:<28} total={total*1000:7.1f}ms  ({len(times)}/{n} ok)"
                else:
                    results[case_label][n][engine] = None
                    line = f"    {engine:<28} all requests failed"

                lines.append(line)
                print(line)

    lines.append("\n" + "=" * 60)

    with open(RESULTS_FILE, "a") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\nResults written to {RESULTS_FILE}")

    # CSV layout — one block per test case, separated by a blank row
    # Sheets reads first column as X axis (request count), engines as series headers
    #
    # Test case: q='' genre=''
    # Number of requests;postgres;elasticsearch;elasticsearch_enriched
    # 1;17,6;2,4;5,2
    # 5;20,9;8,3;25,2
    # ...
    #
    # Test case: q='zelda' genre=''
    # Number of requests;postgres;...

    csv_lines = []
    for case_label, case_data in results.items():
        csv_lines.append(f"Test case: {case_label}")
        csv_lines.append("Number of requests;" + ";".join(ENGINES))
        for n in REQUEST_COUNTS:
            row = [str(n)] + [
                fmt(case_data[n][e]) if case_data[n].get(e) is not None else ""
                for e in ENGINES
            ]
            csv_lines.append(";".join(row))
        csv_lines.append("")  # blank row between blocks

    with open(CSV_FILE, "w") as f:
        f.write("\n".join(csv_lines) + "\n")
    print(f"CSV written to {CSV_FILE}")


if __name__ == "__main__":
    run_benchmark()
