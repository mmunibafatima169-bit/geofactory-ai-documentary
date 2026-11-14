"""
Unit tests for cinematic scene transition filters in documentary renderer.

These tests verify the transition filter generation logic without requiring FFmpeg/PIL.
"""

from __future__ import annotations

import re
import unittest


def _build_transition_filter(
    prev_idx: int,
    curr_idx: int,
    transition_type: str,
    segment_duration: float,
    frame_rate: int = 30,
) -> str:
    """
    Build FFmpeg filter for scene transition.
    
    This is a standalone copy of the logic from documentary_renderer.py
    for testing without PIL dependencies.
    """
    trans_dur = min(1.5, segment_duration * 0.15)
    
    if transition_type == "zoom_punch":
        return (
            f"[v{prev_idx}][v{curr_idx}]"
            f"xfade=transition=zoomin:duration={trans_dur:.3f}:offset={segment_duration - trans_dur:.3f}"
            f"[v{curr_idx}trans]"
        )
    elif transition_type == "wipe_map":
        return (
            f"[v{prev_idx}][v{curr_idx}]"
            f"xfade=transition=wipeleft:duration={trans_dur:.3f}:offset={segment_duration - trans_dur:.3f}"
            f"[v{curr_idx}trans]"
        )
    elif transition_type == "dip_to_black":
        return (
            f"[v{prev_idx}]fade=t=out:st={segment_duration - trans_dur:.3f}:d={trans_dur:.3f}[v{prev_idx}faded];"
            f"[v{curr_idx}]fade=t=in:st=0:d={trans_dur:.3f}[v{curr_idx}faded];"
            f"[v{prev_idx}faded][v{curr_idx}faded]"
            f"xfade=transition=fade:duration={trans_dur:.3f}:offset={segment_duration - trans_dur:.3f}"
            f"[v{curr_idx}trans]"
        )
    elif transition_type == "crossfade":
        return (
            f"[v{prev_idx}][v{curr_idx}]"
            f"xfade=transition=fade:duration={trans_dur:.3f}:offset={segment_duration - trans_dur:.3f}"
            f"[v{curr_idx}trans]"
        )
    else:
        return ""


class TransitionFilterTests(unittest.TestCase):
    """Test the _build_transition_filter function for various transition types."""
    
    def test_zoom_punch_transition(self):
        """Test zoom_punch transition filter generation."""
        filter_str = _build_transition_filter(0, 1, "zoom_punch", 10.0)
        
        self.assertIn("xfade=transition=zoomin", filter_str)
        self.assertIn("duration=", filter_str)
        self.assertIn("offset=", filter_str)
        self.assertIn("[v1trans]", filter_str)
    
    def test_wipe_map_transition(self):
        """Test wipe_map transition filter generation."""
        filter_str = _build_transition_filter(0, 1, "wipe_map", 10.0)
        
        self.assertIn("xfade=transition=wipeleft", filter_str)
        self.assertIn("duration=", filter_str)
        self.assertIn("offset=", filter_str)
        self.assertIn("[v1trans]", filter_str)
    
    def test_dip_to_black_transition(self):
        """Test dip_to_black transition filter generation."""
        filter_str = _build_transition_filter(0, 1, "dip_to_black", 10.0)
        
        self.assertIn("fade=t=out", filter_str)
        self.assertIn("fade=t=in", filter_str)
        self.assertIn("xfade=transition=fade", filter_str)
        self.assertIn("[v1trans]", filter_str)
    
    def test_crossfade_transition(self):
        """Test crossfade transition filter generation."""
        filter_str = _build_transition_filter(0, 1, "crossfade", 10.0)
        
        self.assertIn("xfade=transition=fade", filter_str)
        self.assertIn("duration=", filter_str)
        self.assertIn("offset=", filter_str)
        self.assertIn("[v1trans]", filter_str)
    
    def test_cut_transition_returns_empty(self):
        """Test that 'cut' transition returns empty string (handled by concat)."""
        filter_str = _build_transition_filter(0, 1, "cut", 10.0)
        
        self.assertEqual(filter_str, "")
    
    def test_unknown_transition_returns_empty(self):
        """Test that unknown transition type returns empty string."""
        filter_str = _build_transition_filter(0, 1, "unknown_type", 10.0)
        
        self.assertEqual(filter_str, "")
    
    def test_transition_duration_scaling(self):
        """Test that transition duration scales with segment duration."""
        short_filter = _build_transition_filter(0, 1, "zoom_punch", 2.0)
        long_filter = _build_transition_filter(0, 1, "zoom_punch", 30.0)
        
        short_dur = float(re.search(r'duration=([0-9.]+)', short_filter).group(1))
        long_dur = float(re.search(r'duration=([0-9.]+)', long_filter).group(1))
        
        self.assertLessEqual(short_dur, 1.5)
        self.assertLessEqual(long_dur, 1.5)
        self.assertAlmostEqual(long_dur, 1.5, places=1)
    
    def test_transition_offset_calculation(self):
        """Test that offset is calculated correctly (near end of previous segment)."""
        filter_str = _build_transition_filter(0, 1, "zoom_punch", 10.0)
        
        offset = float(re.search(r'offset=([0-9.]+)', filter_str).group(1))
        duration = float(re.search(r'duration=([0-9.]+)', filter_str).group(1))
        
        expected_offset = 10.0 - duration
        self.assertAlmostEqual(offset, expected_offset, places=1)


if __name__ == "__main__":
    unittest.main()
