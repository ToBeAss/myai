"""Usage/quota tracking helper for TextToSpeech."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Callable


class TTSUsageTracker:
    """Persist and evaluate monthly TTS usage and quota constraints."""

    def __init__(self, usage_file: Path, voice_tiers: dict):
        self.usage_file = usage_file
        self.voice_tiers = voice_tiers

    def load_usage(self) -> dict:
        if os.path.exists(self.usage_file):
            try:
                with open(self.usage_file, "r") as f:
                    data = json.load(f)
                    if data.get("month") != datetime.now().strftime("%Y-%m"):
                        return self.create_new_usage_data()
                    return data
            except Exception as e:
                print(f"⚠️  Could not load usage data: {e}. Creating new file.")
        return self.create_new_usage_data()

    def create_new_usage_data(self) -> dict:
        return {
            "month": datetime.now().strftime("%Y-%m"),
            "tiers": {tier: 0 for tier in self.voice_tiers.keys()},
            "total_requests": 0,
            "last_updated": datetime.now().isoformat(),
        }

    def save_usage(self, usage_data: dict) -> None:
        try:
            usage_data["last_updated"] = datetime.now().isoformat()
            with open(self.usage_file, "w") as f:
                json.dump(usage_data, f, indent=2)
        except Exception as e:
            print(f"⚠️  Could not save usage data: {e}")

    def update_usage(self, usage_data: dict, voice_name: str, determine_voice_tier: Callable[[str], str], char_count: int) -> dict:
        active_tier = determine_voice_tier(voice_name)
        usage_data["tiers"][active_tier] += char_count
        usage_data["total_requests"] += 1
        self.save_usage(usage_data)
        return usage_data

    def check_and_switch_voice(
        self,
        usage_data: dict,
        voice_name: str,
        using_fallback: bool,
        primary_voice_name: str,
        voice_tier: str,
        fallback_voice: str | None,
        fallback_tier: str | None,
    ) -> tuple[bool, str, bool]:
        if not fallback_voice or not fallback_tier:
            return False, voice_name, using_fallback

        if using_fallback and usage_data.get("month") == datetime.now().strftime("%Y-%m"):
            primary_usage = usage_data["tiers"][voice_tier]
            if primary_usage == 0:
                print(f"🔄 New month detected! Switched back to primary voice: {primary_voice_name}")
                return True, primary_voice_name, False

        if not using_fallback:
            primary_usage = usage_data["tiers"][voice_tier]
            primary_limit = self.voice_tiers[voice_tier]["free_chars"]
            if primary_usage >= primary_limit * 0.99:
                fallback_usage = usage_data["tiers"][fallback_tier]
                fallback_limit = self.voice_tiers[fallback_tier]["free_chars"]
                if fallback_usage < fallback_limit:
                    print(f"🔄 Primary voice quota exhausted. Switching to fallback: {fallback_voice}")
                    return True, fallback_voice, True

        return False, voice_name, using_fallback

    def check_quota(
        self,
        text: str,
        enforce_free_tier: bool,
        usage_data: dict,
        voice_name: str,
        using_fallback: bool,
        fallback_voice: str | None,
        voice_tier: str,
        fallback_tier: str | None,
        determine_voice_tier: Callable[[str], str],
    ) -> tuple[bool, str, str, bool]:
        if not enforce_free_tier:
            return True, "", voice_name, using_fallback

        char_count = len(text)
        active_tier = determine_voice_tier(voice_name)
        current_usage = usage_data["tiers"][active_tier]
        free_limit = self.voice_tiers[active_tier]["free_chars"]

        if current_usage + char_count > free_limit:
            if fallback_voice and fallback_tier and not using_fallback:
                fallback_usage = usage_data["tiers"][fallback_tier]
                fallback_limit = self.voice_tiers[fallback_tier]["free_chars"]

                if fallback_usage + char_count <= fallback_limit:
                    print(f"\n🔄 Primary voice quota exhausted. Automatically switching to fallback: {fallback_voice}")
                    print(f"   Primary ({voice_tier.upper()}): {current_usage:,}/{free_limit:,} used")
                    print(f"   Fallback ({fallback_tier.upper()}): {fallback_usage:,}/{fallback_limit:,} used\n")
                    return True, "", fallback_voice, True

            remaining = free_limit - current_usage
            fallback_info = ""
            if fallback_voice and fallback_tier:
                fallback_usage = usage_data["tiers"][fallback_tier]
                fallback_limit = self.voice_tiers[fallback_tier]["free_chars"]
                fallback_info = f"   Fallback ({fallback_tier.upper()}): {fallback_usage:,}/{fallback_limit:,} used\n"

            message = (
                f"❌ FREE TIER LIMIT EXCEEDED!\n"
                f"   Active Voice: {voice_name}\n"
                f"   Voice Tier: {active_tier.upper()}\n"
                f"   This request: {char_count:,} characters\n"
                f"   Current usage: {current_usage:,}/{free_limit:,} characters\n"
                f"   Remaining: {remaining:,} characters\n"
                f"{fallback_info}"
                f"   To continue using TTS, either:\n"
                f"   1. Wait until next month (resets on 1st)\n"
                f"   2. Switch to a different voice with available quota\n"
                f"   3. Set enforce_free_tier=False (will incur charges)\n"
            )
            return False, message, voice_name, using_fallback

        return True, "", voice_name, using_fallback

    def usage_stats(
        self,
        usage_data: dict,
        voice_name: str,
        using_fallback: bool,
        primary_voice_name: str,
        voice_tier: str,
        fallback_voice: str | None,
        fallback_tier: str | None,
    ) -> dict:
        stats = {
            "month": usage_data["month"],
            "active_voice": voice_name,
            "using_fallback": using_fallback,
            "primary_voice": primary_voice_name,
            "primary_tier": voice_tier,
            "primary_usage": usage_data["tiers"][voice_tier],
            "primary_limit": self.voice_tiers[voice_tier]["free_chars"],
            "primary_remaining": self.voice_tiers[voice_tier]["free_chars"] - usage_data["tiers"][voice_tier],
            "total_requests": usage_data["total_requests"],
            "all_tiers": usage_data["tiers"],
        }
        stats["primary_percentage_used"] = (stats["primary_usage"] / stats["primary_limit"]) * 100

        if fallback_voice and fallback_tier:
            stats["fallback_voice"] = fallback_voice
            stats["fallback_tier"] = fallback_tier
            stats["fallback_usage"] = usage_data["tiers"][fallback_tier]
            stats["fallback_limit"] = self.voice_tiers[fallback_tier]["free_chars"]
            stats["fallback_remaining"] = stats["fallback_limit"] - stats["fallback_usage"]
            stats["fallback_percentage_used"] = (stats["fallback_usage"] / stats["fallback_limit"]) * 100

        return stats

    def print_usage_stats(
        self,
        usage_data: dict,
        using_fallback: bool,
        voice_tier: str,
        fallback_voice: str | None,
        fallback_tier: str | None,
        enforce_free_tier: bool,
    ) -> None:
        print(f"📊 Monthly Usage ({usage_data['month']}):")

        primary_usage = usage_data["tiers"][voice_tier]
        primary_limit = self.voice_tiers[voice_tier]["free_chars"]
        primary_percentage = (primary_usage / primary_limit) * 100

        active_marker = "🎤" if not using_fallback else "💤"
        print(f"   {active_marker} Primary ({voice_tier.upper()}): {primary_usage:,}/{primary_limit:,} chars ({primary_percentage:.1f}%)")

        if fallback_voice and fallback_tier:
            fallback_usage = usage_data["tiers"][fallback_tier]
            fallback_limit = self.voice_tiers[fallback_tier]["free_chars"]
            fallback_percentage = (fallback_usage / fallback_limit) * 100
            active_marker = "🎤" if using_fallback else "💤"
            print(f"   {active_marker} Fallback ({fallback_tier.upper()}): {fallback_usage:,}/{fallback_limit:,} chars ({fallback_percentage:.1f}%)")

        if using_fallback:
            print("   ℹ️  Currently using: FALLBACK voice")
        else:
            print("   ℹ️  Currently using: PRIMARY voice")
            if primary_percentage > 80:
                print("   ⚠️  WARNING: Primary voice approaching limit! Will auto-switch to fallback.")

        if enforce_free_tier:
            print("   🛡️  Free tier protection: ENABLED")
        else:
            print("   ⚠️  Free tier protection: DISABLED (charges may apply)")
