"""M167: copy Save As before the first MY HIGH SCHOOL menu evaluation.

EA changes the save slot and display name during the same loaded home zone,
but the school's arrival watcher may not run until later. The very first
menu test must see the new active school settings and its sixteen pupils.
"""
import unittest

from tests.test_m166_multiple_save_as import MultipleSaveAsGameIdentityTests
from mhs_m2_store import RosterStore
from mhs_m2_roster import SchoolRoster
from mhs34_settings import SettingsStore
import mhs_m2_game_bridge as bridge


class ImmediateSaveAsTests(MultipleSaveAsGameIdentityTests):
    """Use M166's real school registry and mocked EA persistence services."""

    def setUp(self):
        super().setUp()
        # M166 base tests start at an EA scratch slot. For Save As the
        # actual EA number changes while keeping the *same* zone object.
        self.slot = 10
        self.title = 'Originale'
        self.assertEqual(bridge.current_slot(allow_travel=True), '10')

    def test_menu_reads_active_school_immediately_after_first_and_second_copy(self):
        # Save is an overwrite of the existing game, never creates a
        # second external roster.
        self.assertEqual(bridge.current_slot(allow_travel=True), '10')
        self.title = 'Copia 1'
        self.slot = 17
        # The next call is from the pie-menu visibility predicate, BEFORE
        # the school's timer or lifecycle callback has refreshed.
        first = bridge.current_slot(allow_travel=True)
        self.assertEqual(first, '17')
        self.assertTrue(SettingsStore(self.folder).load(first).active)
        self.assertEqual(len(RosterStore(self.folder).load(first).assignments),
                         16)
        self.assertEqual(self.named.unique(self.guid, 'Copia 1'), '17')
        self.assertEqual(bridge.current_slot(allow_travel=True), '17')

        # One enrolled student is changed only in Copy 1; Copy 2 must
        # inherit that version and Original must remain untouched.
        amended = dict(RosterStore(self.folder).load('17').assignments)
        amended.pop('115')
        amended['116'] = 2
        RosterStore(self.folder).save(
            '17', SchoolRoster('17', amended))
        self.title = 'Copia 2'
        self.slot = 18
        second = bridge.current_slot(allow_travel=True)
        self.assertEqual(second, '18')
        self.assertTrue(SettingsStore(self.folder).load(second).active)
        self.assertIn('116', RosterStore(self.folder).load(second).assignments)
        self.assertNotIn('116',
                         RosterStore(self.folder).load('10').assignments)
        self.assertEqual(self.named.unique(self.guid, 'Copia 2'), '18')

        # Cold restart each independently, EA returns its scratch slot.
        for title, expected in (
                ('Originale', '10'), ('Copia 1', '17'),
                ('Copia 2', '18')):
            self.cold_start()
            self.title = title
            self.slot = 0xffffffff
            resolved = bridge.current_slot(allow_travel=True)
            self.assertEqual(resolved, expected)
            self.assertTrue(SettingsStore(self.folder).load(resolved).active)

    def test_title_arrives_before_new_real_slot_never_aliases_original(self):
        # The EA save-dialog title may update before the numeric slot.
        self.title = 'Copia 1'
        self.slot = 10
        with self.assertRaisesRegex(bridge.BridgeError, 'in corso'):
            bridge.current_slot(allow_travel=True)
        self.assertIsNone(self.named.unique(self.guid, 'Copia 1'))
        self.assertEqual(bridge._SLOT_GUARD.slot, '10')
        # As soon as EA announces the new numeric slot, clone before
        # exposing the new school menu.
        self.slot = 17
        self.assertEqual(bridge.current_slot(allow_travel=True), '17')
        self.assertTrue(SettingsStore(self.folder).load('17').active)

    def test_real_slot_arrives_before_title_never_rebinds_original_name(self):
        self.slot = 17
        self.title = 'Originale'
        with self.assertRaisesRegex(bridge.BridgeError,
                                    'aggiornamento'):
            bridge.current_slot(allow_travel=True)
        self.assertEqual(self.named.unique(self.guid, 'Originale'), '10')
        self.title = 'Copia 1'
        self.assertEqual(bridge.current_slot(allow_travel=True), '17')
        self.assertEqual(self.named.unique(self.guid, 'Copia 1'), '17')

    def test_different_zone_does_not_copy_other_saved_school(self):
        self.zone = object()
        self.title = 'Unaltra partita'
        self.slot = 19
        self.assertEqual(bridge.current_slot(allow_travel=True), '19')
        self.assertFalse(SettingsStore(self.folder).load('19').active)
        self.assertIsNone(self.named.unique(self.guid, 'Unaltra partita'))


if __name__ == '__main__':
    unittest.main()
