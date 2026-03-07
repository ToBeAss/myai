"""Wake-word analytics and reporting helpers."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from myai.paths import data_file


class WakeWordMetrics:
    """Track wake-word activation metrics for analytics and optimization."""

    def __init__(self, metrics_file: Optional[Path] = None):
        self.metrics_file = Path(metrics_file) if metrics_file else data_file("wake_word_metrics.json")
        self.session_start = time.time()

        # Session counters
        self.true_positives = 0
        self.false_positives = 0
        self.false_negatives = 0
        self.true_negatives = 0

        # Detailed activation history
        self.activation_log = []

        # Confidence distribution buckets
        self.confidence_distribution = {
            "80-100": {"count": 0, "engaged": 0},
            "60-79": {"count": 0, "engaged": 0},
            "40-59": {"count": 0, "engaged": 0},
            "0-39": {"count": 0, "engaged": 0},
        }

        self._load_metrics()

    def _load_metrics(self):
        """Load historical metrics from file if present."""
        if os.path.exists(self.metrics_file):
            try:
                with open(self.metrics_file, "r") as f:
                    _ = json.load(f)
            except Exception as e:
                print(f"⚠️ Could not load metrics: {e}")

    def _save_metrics(self):
        """Persist current metrics to disk."""
        try:
            data = {
                "session_start": datetime.fromtimestamp(self.session_start).isoformat(),
                "true_positives": self.true_positives,
                "false_positives": self.false_positives,
                "false_negatives": self.false_negatives,
                "true_negatives": self.true_negatives,
                "confidence_distribution": self.confidence_distribution,
                "recent_activations": self.activation_log[-50:],
            }
            with open(self.metrics_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"⚠️ Could not save metrics: {e}")

    def log_activation(self, transcription: str, confidence: int, wake_word_position: int):
        """Log a wake-word activation attempt."""
        entry = {
            "timestamp": time.time(),
            "transcription": transcription[:100],
            "confidence": confidence,
            "position": wake_word_position,
            "outcome": "pending",
        }
        self.activation_log.append(entry)

        if confidence >= 80:
            self.confidence_distribution["80-100"]["count"] += 1
        elif confidence >= 60:
            self.confidence_distribution["60-79"]["count"] += 1
        elif confidence >= 40:
            self.confidence_distribution["40-59"]["count"] += 1
        else:
            self.confidence_distribution["0-39"]["count"] += 1

    def log_outcome(self, engaged: bool):
        """Log whether the latest activation was a true or false positive."""
        if not self.activation_log:
            return

        last_entry = self.activation_log[-1]
        confidence = last_entry["confidence"]

        if engaged:
            last_entry["outcome"] = "true_positive"
            self.true_positives += 1

            if confidence >= 80:
                self.confidence_distribution["80-100"]["engaged"] += 1
            elif confidence >= 60:
                self.confidence_distribution["60-79"]["engaged"] += 1
            elif confidence >= 40:
                self.confidence_distribution["40-59"]["engaged"] += 1
        else:
            last_entry["outcome"] = "false_positive"
            self.false_positives += 1

        self._save_metrics()

    def log_false_negative(self, transcription: str):
        """Log a missed activation event."""
        self.false_negatives += 1
        entry = {
            "timestamp": time.time(),
            "transcription": transcription[:100],
            "confidence": 0,
            "position": -1,
            "outcome": "false_negative",
        }
        self.activation_log.append(entry)
        self._save_metrics()

    def log_true_negative(self):
        """Log correctly ignored non-activation audio."""
        self.true_negatives += 1

    def generate_report(self) -> dict:
        """Generate metrics summary for the current session."""
        total_activations = self.true_positives + self.false_positives

        report = {
            "session_duration": time.time() - self.session_start,
            "total_activations": total_activations,
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "true_negatives": self.true_negatives,
            "success_rate": (self.true_positives / total_activations * 100) if total_activations > 0 else 0,
            "confidence_distribution": {},
        }

        for range_key, data in self.confidence_distribution.items():
            count = data["count"]
            engaged = data["engaged"]
            engagement_rate = (engaged / count * 100) if count > 0 else 0
            report["confidence_distribution"][range_key] = {
                "activations": count,
                "engagement_rate": engagement_rate,
            }

        return report

    def print_report(self):
        """Print a human-readable metrics report."""
        report = self.generate_report()

        print("\n" + "=" * 60)
        print("📊 WAKE WORD PERFORMANCE METRICS")
        print("=" * 60)
        print(f"⏱️  Session Duration: {report['session_duration']:.1f} seconds")
        print(f"🎯 Total Activations: {report['total_activations']}")
        print(f"✅ True Positives: {report['true_positives']} ({report['success_rate']:.1f}%)")
        print(f"❌ False Positives: {report['false_positives']}")
        print(f"😞 False Negatives: {report['false_negatives']}")
        print(f"✓  True Negatives: {report['true_negatives']}")
        print("\n📈 Confidence Distribution:")
        for range_key in ["80-100", "60-79", "40-59", "0-39"]:
            data = report["confidence_distribution"][range_key]
            print(f"   {range_key}: {data['activations']} activations ({data['engagement_rate']:.0f}% engagement)")
        print("=" * 60 + "\n")
