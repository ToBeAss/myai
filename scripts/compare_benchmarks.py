"""
Compare Benchmark Results

Analyzes benchmark_results.csv to show performance trends and comparisons.
Useful for tracking improvements over time and comparing different test scenarios.

Usage:
    python scripts/compare_benchmarks.py                    # Show all results
    python scripts/compare_benchmarks.py --test short_weather  # Filter by test
    python scripts/compare_benchmarks.py --latest 5         # Show last 5 runs
"""

import csv
import argparse
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Union

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if SRC_PATH.exists():
    sys.path.insert(0, str(SRC_PATH))

from myai.paths import data_file
from collections import defaultdict


def load_results(csv_file: Optional[Union[str, Path]] = None) -> List[Dict]:
    """Load benchmark results from CSV."""
    csv_path = Path(csv_file) if csv_file else data_file('benchmark_results.csv')

    if not csv_path.exists():
        print(f"❌ No results file found: {csv_path}")
        print("Run benchmarks first: python scripts/benchmark_pipeline.py tests/audio/short_weather.wav --save")
        return []
    
    results = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert numeric fields
            for key in row:
                if key not in ['timestamp', 'test_name', 'approach', 'bottleneck_component']:
                    try:
                        row[key] = float(row[key])
                    except ValueError:
                        pass
            results.append(row)
    
    return results


def print_summary_table(results: List[Dict]):
    """Print formatted table of results."""
    if not results:
        print("No results to display.")
        return
    
    print("\n" + "="*120)
    print(f"📊 BENCHMARK RESULTS SUMMARY ({len(results)} runs)")
    print("="*120)
    
    # Header
    print(f"{'Timestamp':<20} {'Test':<20} {'TTFS (ms)':<12} {'STT':<10} {'LLM':<10} {'TTS':<10} {'Bottleneck':<15}")
    print("-"*120)
    
    for result in results:
        timestamp = datetime.fromisoformat(result['timestamp']).strftime('%Y-%m-%d %H:%M')
        test_name = result['test_name'][:18]
        ttfs = result['time_to_first_sound'] * 1000
        stt = result['stt_total'] * 1000
        llm = result['llm_total'] * 1000
        tts = result['tts_total'] * 1000
        bottleneck = f"{result['bottleneck_component']} ({result['bottleneck_percentage']:.0f}%)"
        
        # Color code TTFS
        if ttfs < 500:
            ttfs_str = f"✅ {ttfs:>7.0f}"
        elif ttfs < 800:
            ttfs_str = f"👍 {ttfs:>7.0f}"
        elif ttfs < 1200:
            ttfs_str = f"✓  {ttfs:>7.0f}"
        else:
            ttfs_str = f"⚠️  {ttfs:>7.0f}"
        
        print(f"{timestamp:<20} {test_name:<20} {ttfs_str:<12} {stt:>7.0f}ms  {llm:>7.0f}ms  {tts:>7.0f}ms  {bottleneck:<15}")
    
    print("="*120)


def print_test_comparison(results: List[Dict], test_name: str):
    """Compare results for a specific test over time."""
    test_results = [r for r in results if r['test_name'] == test_name]
    
    if not test_results:
        print(f"❌ No results found for test: {test_name}")
        return
    
    print("\n" + "="*70)
    print(f"📈 PERFORMANCE TREND: {test_name}")
    print("="*70)
    
    print(f"\n{'Run':<6} {'Date':<12} {'TTFS':<10} {'STT':<10} {'LLM':<10} {'TTS':<10}")
    print("-"*70)
    
    for i, result in enumerate(test_results, 1):
        date = datetime.fromisoformat(result['timestamp']).strftime('%m/%d %H:%M')
        ttfs = result['time_to_first_sound'] * 1000
        stt = result['stt_first_chunk'] * 1000
        llm = result['llm_ttft'] * 1000
        tts = result['tts_first_audio'] * 1000
        
        print(f"#{i:<5} {date:<12} {ttfs:>7.0f}ms  {stt:>7.0f}ms  {llm:>7.0f}ms  {tts:>7.0f}ms")
    
    # Show improvement
    if len(test_results) > 1:
        first_ttfs = test_results[0]['time_to_first_sound'] * 1000
        last_ttfs = test_results[-1]['time_to_first_sound'] * 1000
        improvement = first_ttfs - last_ttfs
        improvement_pct = (improvement / first_ttfs * 100) if first_ttfs > 0 else 0
        
        print("-"*70)
        if improvement > 0:
            print(f"🚀 Improvement: {improvement:.0f}ms faster ({improvement_pct:.1f}% improvement)")
        elif improvement < 0:
            print(f"⚠️  Regression: {abs(improvement):.0f}ms slower ({abs(improvement_pct):.1f}% slower)")
        else:
            print("➡️  No change")
    
    print("="*70)


def print_statistics(results: List[Dict]):
    """Print statistical summary."""
    if not results:
        return
    
    # Group by test name
    by_test = defaultdict(list)
    for result in results:
        by_test[result['test_name']].append(result['time_to_first_sound'])
    
    print("\n" + "="*70)
    print("📊 STATISTICS BY TEST")
    print("="*70)
    
    print(f"\n{'Test Name':<25} {'Runs':<8} {'Avg TTFS':<12} {'Min':<10} {'Max':<10}")
    print("-"*70)
    
    for test_name, ttfs_values in sorted(by_test.items()):
        avg = sum(ttfs_values) / len(ttfs_values) * 1000
        min_val = min(ttfs_values) * 1000
        max_val = max(ttfs_values) * 1000
        
        print(f"{test_name:<25} {len(ttfs_values):<8} {avg:>9.0f}ms  {min_val:>7.0f}ms  {max_val:>7.0f}ms")
    
    print("="*70)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Compare and analyze benchmark results'
    )
    parser.add_argument(
        '--test',
        help='Filter by test name'
    )
    parser.add_argument(
        '--latest',
        type=int,
        help='Show only the N most recent runs'
    )
    
    args = parser.parse_args()
    
    # Load results
    results = load_results()
    
    if not results:
        return
    
    # Sort by timestamp (newest first)
    results.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Apply filters
    if args.latest:
        results = results[:args.latest]
    
    if args.test:
        print_test_comparison(results, args.test)
    else:
        print_summary_table(results)
        print_statistics(results)
        
        print("\n💡 Tips:")
        print("  • To see trends for a specific test: python compare_benchmarks.py --test short_weather")
        print("  • To see recent runs only: python compare_benchmarks.py --latest 10")


if __name__ == "__main__":
    main()
