#!/usr/bin/env python3
"""Unit tests for the trail filter: python3 script/test_build_trail_pack.py"""
import os, sys, unittest

sys.path.insert(0, os.path.dirname(__file__))
from build_trail_pack import is_kept, normalized_street_name  # noqa: E402


class TrailFilterTests(unittest.TestCase):
    streets = {normalized_street_name("Pine Street"), normalized_street_name("Main  street")}

    def test_paths_tracks_and_steps_are_kept_without_a_name(self):
        for kind in ("path", "track", "bridleway", "steps"):
            self.assertTrue(is_kept(kind, None))

    def test_named_footway_that_is_not_a_street_is_kept(self):
        self.assertTrue(is_kept("footway", "Lackawanna River Heritage Trail", None, self.streets))

    def test_unnamed_footway_is_dropped(self):
        self.assertFalse(is_kept("footway", None))

    def test_sidewalks_and_crossings_are_dropped(self):
        self.assertFalse(is_kept("footway", "Heritage Walk", "sidewalk"))
        self.assertFalse(is_kept("footway", "Heritage Walk", "crossing"))
        self.assertFalse(is_kept("path", None, "sidewalk"))

    def test_footway_named_like_a_street_is_dropped(self):
        self.assertFalse(is_kept("footway", "Pine Street", None, self.streets))
        self.assertFalse(is_kept("footway", "main street", None, self.streets))

    def test_paths_and_steps_named_like_a_street_are_dropped(self):
        self.assertFalse(is_kept("path", "Pine Street", None, self.streets))
        self.assertFalse(is_kept("steps", "Pine Street", None, self.streets))

    def test_a_track_named_like_a_street_is_dropped(self):
        self.assertFalse(is_kept("track", "Pine Street", None, self.streets))   # unpaved town alley

    def test_a_bridleway_sharing_a_street_name_is_kept(self):
        self.assertTrue(is_kept("bridleway", "Pine Street", None, self.streets))

    def test_service_roads_do_not_count_as_streets(self):
        from build_trail_pack import STREET_KINDS
        self.assertNotIn("service", STREET_KINDS)

    def test_named_cycleway_is_kept(self):
        self.assertTrue(is_kept("cycleway", "Lackawanna River Heritage Trail", None, self.streets))

    def test_unnamed_cycleway_is_dropped(self):
        self.assertFalse(is_kept("cycleway", None))

    def test_cycleway_crossings_and_street_named_bike_lanes_are_dropped(self):
        self.assertFalse(is_kept("cycleway", "Heritage Trail", None, self.streets, "crossing"))
        self.assertFalse(is_kept("cycleway", "Heritage Trail", "crossing", self.streets))
        self.assertFalse(is_kept("cycleway", "Pine Street", None, self.streets))


if __name__ == "__main__":
    unittest.main()
