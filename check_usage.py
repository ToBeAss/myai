#!/usr/bin/env python3
"""
Utility script to monitor Google Cloud TTS usage and show statistics.
Usage: python check_usage.py
"""

import json
import os
from datetime import datetime
from lib.text_to_speech import TextToSpeech

def format_bar(percentage: float, width: int = 40) -> str:
    """Create a visual progress bar."""
    filled = int(width * percentage / 100)
    bar = '█' * filled + '░' * (width - filled)
    return bar

def main():
    usage_file = "tts_usage.json"
    
    if not os.path.exists(usage_file):
        print("📊 No usage data found yet.")
        print("💡 Usage tracking will begin when you first use TTS.")
        return 0
    
    try:
        with open(usage_file, 'r') as f:
            data = json.load(f)
        
        print("=" * 80)
        print("📊 GOOGLE CLOUD TTS USAGE REPORT")
        print("=" * 80)
        print(f"Month: {data['month']}")
        print(f"Last Updated: {data['last_updated']}")
        print(f"Total Requests: {data['total_requests']}")
        print()
        
        # Get tier limits
        tiers = TextToSpeech.VOICE_TIERS
        
        print("📈 Usage by Voice Tier:")
        print("-" * 80)
        
        total_used = 0
        for tier, usage in data['tiers'].items():
            if tier in tiers and usage > 0:
                limit = tiers[tier]['free_chars']
                percentage = (usage / limit) * 100
                remaining = limit - usage
                
                print(f"\n🎯 {tier.upper()}")
                print(f"   Limit: {limit:,} characters/month (free)")
                print(f"   Used:  {usage:,} characters ({percentage:.1f}%)")
                print(f"   Free:  {remaining:,} characters")
                print(f"   [{format_bar(percentage)}] {percentage:.1f}%")
                
                if percentage > 90:
                    print(f"   🚨 CRITICAL: Only {remaining:,} characters remaining!")
                elif percentage > 75:
                    print(f"   ⚠️  WARNING: Approaching limit")
                elif percentage > 50:
                    print(f"   ℹ️  INFO: Over halfway through quota")
                
                total_used += usage
        
        if total_used == 0:
            print("No usage recorded yet for this month.")
        
        print("\n" + "=" * 80)
        print("💡 Tips:")
        print("   • Use STANDARD voices (4M free/month) instead of premium voices")
        print("   • Keep responses concise to save characters")
        print("   • Usage resets on the 1st of each month")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Error reading usage data: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
