import argparse
import asyncio
import json
import subprocess
import time
from pathlib import Path

from load_tester import Endpoint, WeightedLoadTester


def _restart_monolith(project_root: Path) -> None:
    command = ["docker", "compose", "restart", "monolith"]
    subprocess.run(command, cwd=project_root, check=True)


def _format_report(label: str, result) -> dict:
    report = {
        "scenario": label,
        "duration_seconds": round(result.finished_at - result.started_at, 2),
        "totals": {
            "attempted": result.total_attempted,
            "succeeded": result.total_succeeded,
            "failed": result.total_failed,
            "lost_ratio": round(
                (result.total_failed / result.total_attempted) if result.total_attempted else 0.0,
                4,
            ),
        },
        "per_endpoint": {},
    }

    for name, stat in result.per_endpoint.items():
        report["per_endpoint"][name] = {
            "attempted": stat.attempted,
            "succeeded": stat.succeeded,
            "failed": stat.failed,
            "lost_ratio": round((stat.failed / stat.attempted) if stat.attempted else 0.0, 4),
        }

    return report


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run monolith restart loss experiment.")
    parser.add_argument("--duration", type=float, default=45.0, help="Total test duration in seconds.")
    parser.add_argument(
        "--restart-at",
        type=float,
        default=15.0,
        help="Seconds from test start to restart the monolith.",
    )
    parser.add_argument("--rps", type=float, default=40.0, help="Approximate global requests/sec.")
    parser.add_argument("--workers", type=int, default=12, help="Concurrent request workers.")
    parser.add_argument(
        "--output",
        type=str,
        default="",
        help="Optional path to save JSON report.",
    )

    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]

    endpoints = [
        Endpoint("purchase", "POST", "http://localhost:8000/purchase", 0.4),
        Endpoint("download", "POST", "http://localhost:8000/download", 0.4),
        Endpoint("analytics", "GET", "http://localhost:8000/analytics", 0.2),
    ]

    load_tester = WeightedLoadTester(
        endpoints=endpoints,
        requests_per_second=args.rps,
        worker_count=args.workers,
    )

    print("Running monolith experiment...")
    print(f"  Duration: {args.duration}s")
    print(f"  Restart at: {args.restart_at}s")
    print("  Target container: monolith")
    print(f"  Approx RPS: {args.rps}")
    print(f"  Workers: {args.workers}")

    async def disruption() -> None:
        print(f"[{time.strftime('%H:%M:%S')}] Restarting monolith ...")
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _restart_monolith, project_root)
        print(f"[{time.strftime('%H:%M:%S')}] Restart complete.")

    result = await load_tester.run_for_duration(
        duration_seconds=args.duration,
        disruption_at_seconds=args.restart_at,
        disruption_coro=disruption,
    )

    report = _format_report("monolith_restart", result)

    print("\n=== Experiment Result ===")
    print(json.dumps(report, indent=2))

    if args.output:
        output_path = Path(args.output).resolve()
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nSaved report to {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
