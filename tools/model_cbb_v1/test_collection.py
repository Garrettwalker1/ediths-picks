#!/usr/bin/env python3
"""Offline contract tests for the basketball collector."""
import datetime as dt
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import collect_espn as c

class CollectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = patch.object(c, 'ROOT', Path(self.temp.name))
        self.root.start()
    def tearDown(self):
        self.root.stop(); self.temp.cleanup()
    def game(self, state='post'):
        return {'id': '1', 'date': '2030-01-01T20:00Z', 'name': 'Away at Home',
                'status': {'type': {'state': state, 'completed': state == 'post'}},
                'competition': {}}
    def box(self):
        return {'boxscore': {'teams': [{'statistics': [{'name': 'points', 'displayValue': '70'}]}] * 2,
                'players': [{'statistics': [{'athletes': [{'athlete': {'id': '2'}, 'stats': ['20']}]}]}] * 2}}
    def test_empty_nested_box_not_complete(self):
        d = self.box(); self.assertTrue(c.complete_box(d))
        d['boxscore']['players'][0]['statistics'][0]['athletes'] = []
        self.assertFalse(c.complete_box(d))
        self.assertFalse(c.complete_box({'boxscore': {'teams': [{}, {}], 'players': [{}, {}]}}))
    def test_repeat_final_is_not_duplicated(self):
        with patch.object(c, 'scoreboard', return_value=([self.game()], {})), patch.object(c, 'get', return_value=(self.box(), {})) as fetch:
            c.collect(['20300101'], 10)
            r = c.collect(['20300101'], 10)
        self.assertEqual(r['finals_total'], 1)
        self.assertEqual(r['summaries_fetched'], 0)
        self.assertEqual(fetch.call_count, 1)
    def test_odds_covers_no_line_and_started(self):
        pre = self.game('pre'); live = dict(self.game('in'), id='2')
        summary = {'header': {'competitions': [{'date': pre['date'], 'status': {'type': {'state': 'pre'}}}]}}
        with patch.object(c, 'scoreboard', return_value=([pre, live], {})), patch.object(c, 'get', return_value=(summary, {'received_at': '2030-01-01T19:00:00+00:00'})):
            r = c.odds('20300101')
        self.assertEqual(r['counts'], {'no_line': 1, 'not_pregame': 1})
    def test_summary_that_started_is_not_pregame(self):
        summary = {'header': {'competitions': [{'date': '2030-01-01T20:00Z', 'status': {'type': {'state': 'in'}}}]}, 'pickcenter': [{'spread': 1}]}
        with patch.object(c, 'scoreboard', return_value=([self.game('pre')], {})), patch.object(c, 'get', return_value=(summary, {'received_at': '2030-01-01T20:01:00+00:00'})):
            r = c.odds('20300101')
        self.assertEqual(r['counts'], {'not_verified_pregame': 1})

if __name__ == '__main__':
    unittest.main()
