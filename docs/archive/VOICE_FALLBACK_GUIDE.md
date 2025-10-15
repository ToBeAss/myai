# 🔄 Google Cloud TTS - Automatic Voice Fallback Guide

## Overview

Your TTS system now supports **automatic voice fallback**! This means you can use premium voices (like Chirp3-HD) until you hit the free tier limit, then automatically switch to Standard voices for the rest of the month.

## How It Works

### 1️⃣ Start of Month
- System uses your **primary voice** (e.g., Chirp3-HD-Achernar)
- Premium quality, limited to 100,000 characters/month

### 2️⃣ When Primary Quota Exhausted
- System **automatically switches** to your **fallback voice** (e.g., Standard-A)
- Still good quality, but now you have 4,000,000 characters/month available

### 3️⃣ Next Month
- On the 1st of the month, quotas reset
- System **automatically switches back** to your premium primary voice

## Configuration

### Basic Setup (main_continuous.py)

```python
tts = TextToSpeech(
    voice_name="en-GB-Chirp3-HD-Achernar",  # Premium voice (primary)
    language_code="en-GB",
    speaking_rate=1.1,
    pitch=0.0,
    enforce_free_tier=True,              # Stay within free tier
    fallback_voice="en-GB-Standard-A"    # Fallback voice when primary exhausted
)
```

### Voice Recommendations

#### For British English

**Primary Voice Options (100k free/month):**
- `en-GB-Chirp3-HD-Achernar` - Natural, premium quality
- `en-GB-Chirp3-HD-Enceladus` - Alternative premium voice
- `en-GB-Journey-D` - Natural male voice
- `en-GB-Journey-F` - Natural female voice

**Fallback Voice Options (4M free/month):**
- `en-GB-Standard-A` - Female, clear
- `en-GB-Standard-B` - Male, natural
- `en-GB-Standard-C` - Female, warm
- `en-GB-Standard-D` - Male, professional
- `en-GB-Standard-F` - Female, friendly

#### For US English

**Primary Voice Options (100k free/month):**
- `en-US-Journey-D` - Natural male voice
- `en-US-Journey-F` - Natural female voice

**Fallback Voice Options (4M free/month):**
- `en-US-Standard-A` - Male
- `en-US-Standard-C` - Female
- `en-US-Standard-D` - Male
- `en-US-Standard-E` - Female

## Monitoring Your Usage

### Check Current Status

```bash
python check_usage.py
```

This shows:
- Current month's usage for each tier
- Which voice is currently active (primary or fallback)
- Visual progress bars
- Warnings when approaching limits

### Example Output

```
📊 GOOGLE CLOUD TTS USAGE REPORT
================================================================================
Month: 2025-10
Last Updated: 2025-10-15T14:30:00
Total Requests: 250

📈 Usage by Voice Tier:
--------------------------------------------------------------------------------

🎯 CHIRP
   Limit: 100,000 characters/month (free)
   Used:  95,500 characters (95.5%)
   Free:  4,500 characters
   [████████████████████████████████████████] 95.5%
   ⚠️  WARNING: Approaching limit

🎯 STANDARD
   Limit: 4,000,000 characters/month (free)
   Used:  250,000 characters (6.3%)
   Free:  3,750,000 characters
   [██░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 6.3%
```

### During Initialization

The system shows you the current status:

```
🔊 Initializing Google Cloud Text-to-Speech...
✅ Successfully connected to Google Cloud TTS API
📋 Available voices: 421 voices found
✅ Text-to-Speech initialized successfully!
🗣️  Primary Voice: en-GB-Chirp3-HD-Achernar (en-GB)
💎 Primary Tier: CHIRP
📊 Free Tier Limit: 100,000 chars/month
🔄 Fallback Voice: en-GB-Standard-A
💎 Fallback Tier: STANDARD
📊 Fallback Limit: 4,000,000 chars/month
📊 Monthly Usage (2025-10):
   🎤 Primary (CHIRP): 95,500/100,000 chars (95.5%)
   💤 Fallback (STANDARD): 250,000/4,000,000 chars (6.3%)
   ℹ️  Currently using: PRIMARY voice
   ⚠️  WARNING: Primary voice approaching limit! Will auto-switch to fallback.
   🛡️  Free tier protection: ENABLED
```

## Automatic Switching Behavior

### When Primary Exhausted

When you make a request that would exceed the primary voice quota:

```
🔄 Primary voice quota exhausted. Automatically switching to fallback: en-GB-Standard-A
   Primary (CHIRP): 100,000/100,000 used
   Fallback (STANDARD): 250,000/4,000,000 used
```

The system will:
1. Switch to the fallback voice
2. Continue processing your request seamlessly
3. Use the fallback for all subsequent requests this month

### At Month Rollover

On the 1st of each month when quotas reset:

```
🔄 New month detected! Switched back to primary voice: en-GB-Chirp3-HD-Achernar
```

The system automatically switches back to your premium voice.

## Advanced Usage

### Check Active Voice in Code

```python
# Get info about currently active voice
info = tts.get_active_voice_info()
print(f"Active voice: {info['voice_name']}")
print(f"Using primary: {info['is_primary']}")
print(f"Using fallback: {info['is_fallback']}")
```

### Get Detailed Statistics

```python
# Get detailed usage stats
stats = tts.get_usage_stats()
print(f"Primary: {stats['primary_usage']:,}/{stats['primary_limit']:,}")
print(f"Fallback: {stats['fallback_usage']:,}/{stats['fallback_limit']:,}")
print(f"Currently using: {'PRIMARY' if not stats['using_fallback'] else 'FALLBACK'}")
```

### Without Fallback (Original Behavior)

If you want to use just one voice without fallback:

```python
tts = TextToSpeech(
    voice_name="en-GB-Standard-A",
    language_code="en-GB",
    enforce_free_tier=True
    # No fallback_voice specified
)
```

## Character Usage Examples

To help you understand the quotas:

### Primary Voice (100,000 chars/month)

| Response Length | Responses/Month |
|----------------|-----------------|
| 50 chars       | ~2,000         |
| 100 chars      | ~1,000         |
| 200 chars      | ~500           |
| 500 chars      | ~200           |

### Fallback Voice (4,000,000 chars/month)

| Response Length | Responses/Month |
|----------------|-----------------|
| 50 chars       | ~80,000        |
| 100 chars      | ~40,000        |
| 200 chars      | ~20,000        |
| 500 chars      | ~8,000         |

## Best Practices

1. **Use Premium for Important Conversations**: Your first ~1,000-2,000 interactions each month will use the premium voice.

2. **Monitor Usage**: Run `python check_usage.py` periodically to see how you're tracking.

3. **Adjust Response Length**: If you want to maximize premium voice usage, keep responses concise.

4. **Choose Compatible Fallbacks**: Make sure your fallback voice is in the same language as your primary.

5. **Test Both Voices**: Try both voices to ensure the fallback quality is acceptable to you.

## Troubleshooting

### Both Quotas Exhausted

If both voices hit their limits:

```
❌ FREE TIER LIMIT EXCEEDED!
   Active Voice: en-GB-Standard-A
   Voice Tier: STANDARD
   This request: 150 characters
   Current usage: 4,000,000/4,000,000 characters
   Remaining: 0 characters
   Fallback (STANDARD): 4,000,000/4,000,000 used
   
   To continue using TTS, either:
   1. Wait until next month (resets on 1st)
   2. Switch to a different voice with available quota
   3. Set enforce_free_tier=False (will incur charges)
```

Options:
- Wait until the 1st of next month
- Temporarily disable TTS
- Allow paid usage (not recommended if you want to stay free)

### Manual Voice Switch

If you want to manually switch voices:

```python
tts.set_voice("en-GB-Standard-B", "en-GB")
```

## Summary

✅ **Benefits of Fallback System:**
- Use premium voice quality when possible
- Never get surprised by hitting limits
- Automatically optimize for free tier
- Seamless switching - no interruption to your assistant

✅ **Your Current Setup:**
- Primary: Chirp3-HD-Achernar (100k chars) - Premium quality
- Fallback: Standard-A (4M chars) - Good quality, huge quota
- Total: 4.1M free characters per month!

Enjoy your AI assistant with smart voice management! 🎉
