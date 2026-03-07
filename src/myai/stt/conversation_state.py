"""Conversation mode/timer helpers for SpeechToText."""

from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .speech_to_text import SpeechToText


def set_conversation_timeout(stt: "SpeechToText", timeout: float) -> None:
    stt.conversation_timeout = timeout
    print(f"⏱️ Conversation timeout set to {timeout} seconds")


def enter_conversation_mode(stt: "SpeechToText") -> None:
    stt.in_conversation = True
    stt.conversation_last_activity = time.time()
    print(f"💬 Conversation mode active - you can ask follow-up questions for {stt.conversation_timeout} seconds")


def exit_conversation_mode(stt: "SpeechToText") -> None:
    stt.in_conversation = False
    stt.speech_being_processed = False

    if hasattr(stt, "stop_timer_flag"):
        stt.stop_timer_flag = True

    print("👂 Conversation ended, listening for wake words...")


def update_conversation_activity(stt: "SpeechToText") -> None:
    if stt.in_conversation:
        print("🎙️ Speech activity detected - timer will restart after processing")


def check_engagement_timeout(stt: "SpeechToText") -> None:
    if not stt.track_metrics or not stt.waiting_for_engagement:
        return
    if stt.metrics is None:
        stt.waiting_for_engagement = False
        return

    time_since_activation = time.time() - stt.last_activation_time
    if time_since_activation > stt.false_positive_timeout:
        stt.metrics.log_outcome(engaged=False)
        stt.waiting_for_engagement = False


def start_conversation_timer(stt: "SpeechToText") -> None:
    if hasattr(stt, "conversation_timer_thread") and stt.conversation_timer_thread and stt.conversation_timer_thread.is_alive():
        if not stt.in_conversation:
            stt.in_conversation = True
        return

    if hasattr(stt, "stop_timer_flag"):
        stt.stop_timer_flag = True

    stt.stop_timer_flag = False

    def simple_conversation_timer():
        print(f"🕐 Conversation timer started - {stt.conversation_timeout}s for follow-up questions")
        timeout_start_time = time.time()
        timer_was_paused = False

        while stt.in_conversation and not stt.stop_timer_flag:
            current_time = time.time()

            if stt.speech_being_processed:
                if not timer_was_paused:
                    print("⏸️ Timer paused - speech being processed")
                    timer_was_paused = True

                while stt.speech_being_processed and stt.in_conversation and not stt.stop_timer_flag:
                    time.sleep(0.1)

                if stt.in_conversation and not stt.stop_timer_flag:
                    print(f"▶️ Timer restarted - {stt.conversation_timeout}s for follow-up questions")
                    timeout_start_time = time.time()
                    timer_was_paused = False
                    time.sleep(0.3)
                continue

            time_elapsed = current_time - timeout_start_time
            if time_elapsed >= stt.conversation_timeout:
                if stt.in_conversation and not stt.stop_timer_flag:
                    exit_conversation_mode(stt)
                break

            time.sleep(0.1)

        if hasattr(stt, "conversation_timer_thread"):
            stt.conversation_timer_thread = None

    stt.conversation_timer_thread = threading.Thread(target=simple_conversation_timer, daemon=True)
    stt.conversation_timer_thread.start()
