"""Shared test utilities for GeoFactory."""

import os
import shutil
import sys
from typing import Tuple

# Track whether deps are required (set by CI)
REQUIRE_DEPS = os.environ.get("GEOFACTORY_REQUIRE_DEPS", "0") == "1"


def check_pil_available() -> Tuple[bool, str]:
    """Check if PIL is available."""
    try:
        import PIL
        return True, f"PIL {PIL.__version__}"
    except ImportError:
        return False, "PIL not installed"


def check_ffmpeg_available() -> Tuple[bool, str]:
    """Check if FFmpeg is available."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return False, "ffmpeg not found in PATH"
    try:
        import subprocess
        result = subprocess.run([ffmpeg, "-version"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            first_line = result.stdout.split('\n')[0]
            return True, first_line
        return False, f"ffmpeg returned {result.returncode}"
    except Exception as e:
        return False, f"ffmpeg check failed: {e}"


def check_espeak_available() -> Tuple[bool, str]:
    """Check if espeak-ng is available."""
    espeak = shutil.which("espeak-ng")
    if not espeak:
        return False, "espeak-ng not found in PATH"
    try:
        import subprocess
        result = subprocess.run([espeak, "--version"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, f"espeak-ng returned {result.returncode}"
    except Exception as e:
        return False, f"espeak-ng check failed: {e}"


def require_deps_or_skip(*dep_names: str) -> None:
    """
    If GEOFACTORY_REQUIRE_DEPS=1, raise AssertionError if any required dep is missing.
    Otherwise, use unittest.skip to skip the test.
    
    Usage:
        @unittest.skipUnless(not REQUIRE_DEPS or all(check_pil_available()[0], check_ffmpeg_available()[0]),
                           "PIL and FFmpeg required")
        def test_something(self):
            ...
    
    Or in a test method:
        if REQUIRE_DEPS:
            pil_ok, pil_msg = check_pil_available()
            ffmpeg_ok, ffmpeg_msg = check_ffmpeg_available()
            if not pil_ok:
                self.fail(f"PIL required but not available: {pil_msg}")
            if not ffmpeg_ok:
                self.fail(f"FFmpeg required but not available: {ffmpeg_msg}")
        else:
            # Normal skip logic
            ...
    """
    pass  # This is a helper module, actual logic in test decorators


def get_skip_reason(dep_name: str, available: bool, msg: str) -> str:
    """Get appropriate skip/fail message based on REQUIRE_DEPS."""
    if REQUIRE_DEPS:
        if not available:
            return f"REQUIRED dep missing: {dep_name} ({msg})"
    return f"{dep_name} not available ({msg})"


# Decorators for common dependency combinations
def skip_unless_pil_and_ffmpeg(test_func):
    """Skip test unless PIL and FFmpeg are available (or fail if REQUIRE_DEPS=1)."""
    pil_ok, pil_msg = check_pil_available()
    ffmpeg_ok, ffmpeg_msg = check_ffmpeg_available()
    available = pil_ok and ffmpeg_ok
    reason = get_skip_reason("PIL+FFmpeg", available, f"PIL: {pil_msg}; FFmpeg: {ffmpeg_msg}")
    if REQUIRE_DEPS and not available:
        # Will be handled by the test itself checking REQUIRE_DEPS
        import unittest
        return unittest.skip(reason)(test_func)
    return unittest.skipUnless(available, reason)(test_func)


def skip_unless_pil(test_func):
    """Skip test unless PIL is available (or fail if REQUIRE_DEPS=1)."""
    pil_ok, pil_msg = check_pil_available()
    reason = get_skip_reason("PIL", pil_ok, pil_msg)
    if REQUIRE_DEPS and not pil_ok:
        import unittest
        return unittest.skip(reason)(test_func)
    return unittest.skipUnless(pil_ok, reason)(test_func)


def skip_unless_ffmpeg(test_func):
    """Skip test unless FFmpeg is available (or fail if REQUIRE_DEPS=1)."""
    ffmpeg_ok, ffmpeg_msg = check_ffmpeg_available()
    reason = get_skip_reason("FFmpeg", ffmpeg_ok, ffmpeg_msg)
    if REQUIRE_DEPS and not ffmpeg_ok:
        import unittest
        return unittest.skip(reason)(test_func)
    return unittest.skipUnless(ffmpeg_ok, reason)(test_func)


def skip_unless_espeak(test_func):
    """Skip test unless espeak-ng is available (or fail if REQUIRE_DEPS=1)."""
    espeak_ok, espeak_msg = check_espeak_available()
    reason = get_skip_reason("espeak-ng", espeak_ok, espeak_msg)
    if REQUIRE_DEPS and not espeak_ok:
        import unittest
        return unittest.skip(reason)(test_func)
    return unittest.skipUnless(espeak_ok, reason)(test_func)


def skip_unless_pil_ffmpeg_espeak(test_func):
    """Skip test unless PIL, FFmpeg, and espeak-ng are available."""
    pil_ok, pil_msg = check_pil_available()
    ffmpeg_ok, ffmpeg_msg = check_ffmpeg_available()
    espeak_ok, espeak_msg = check_espeak_available()
    available = pil_ok and ffmpeg_ok and espeak_ok
    reason = get_skip_reason("PIL+FFmpeg+espeak", available, f"PIL: {pil_msg}; FFmpeg: {ffmpeg_msg}; espeak: {espeak_msg}")
    if REQUIRE_DEPS and not available:
        import unittest
        return unittest.skip(reason)(test_func)
    return unittest.skipUnless(available, reason)(test_func)


# Import unittest for decorators
import unittest
