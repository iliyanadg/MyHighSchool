"""M52 real picker callback: all three classes, batch checkmark and X."""
import ast,unittest,sys
from pathlib import Path
from types import SimpleNamespace
from tests.test_m51_bulk_transfer import DialogFactory,Store
from mhs_m2_roster import SchoolRoster,RosterError,canonical_sim_id
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'/'m26_withdrawal'))
from mhs26_remove import plan_removal,roster_fingerprint
from tooling.build_m52_removal import package_bytes,EXTRA
from tooling.build_m51_bulk_transfer import package_bytes as m51

class Tests(unittest.TestCase):
    def setup_picker(self,members):
        src=EXTRA.read_text()
        tree=ast.parse(src)
        fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef)
                and x.name=='open_picker')
        store=Store(SchoolRoster('11',members))
        notices=[]
        class Settings(object):
            active=True
            def require_management(self,slot,klass):
                if not self.active:
                    raise RosterError('School off')
        settings=Settings()
        env={
            'current_slot':lambda:'11','_SETTINGS':settings,
            '_STORE':store,'_lookup_sim_info':lambda sid:SimpleNamespace(sim_id=int(sid)),
            'candidate_rows':lambda roster,klass,lookup:[
                lookup(sid) for sid in roster.class_members(klass)],
            'roster_fingerprint':roster_fingerprint,
            'plan_removal':plan_removal,'canonical_sim_id':canonical_sim_id,
            'RosterError':RosterError,'_notice':lambda *args:notices.append(args),
            '_txt':lambda msg:msg,'_str':lambda msg:msg,'_max':lambda count:count,
            'UiSimPicker':DialogFactory,
            'SimPickerRow':lambda sid,checked,tag:SimpleNamespace(sim_id=sid,tag=tag)}
        exec(compile(ast.Module(body=[fn],type_ignores=[]),
            '<M52 real picker>',mode='exec'),env)
        DialogFactory.dialogs=[]
        return env,store,settings,notices

    def test_existing_verified_menu_unchanged(self):
        self.assertEqual(package_bytes(),m51())

    def test_multi_removal_commits_once_and_preserves_other_classes(self):
        env,store,settings,notices=self.setup_picker({
            '101':1,'102':1,'103':1,'201':2,'301':3})
        self.assertTrue(env['open_picker'](1,SimpleNamespace(sim=object())),repr(notices))
        dlg=DialogFactory.dialogs[0]
        self.assertEqual(len(dlg.rows),3)
        self.assertEqual(dlg.kwargs['max_selectable'],3)
        dlg.click(True,(101,102))
        dlg.click(True,(101,102))
        self.assertEqual(store.saved,1)
        self.assertEqual(store.roster.class_members(1),['103'])
        self.assertEqual(store.roster.class_members(2),['201'])
        self.assertEqual(store.roster.class_members(3),['301'])

    def test_x_cancels_even_if_second_callback_accepted(self):
        env,store,settings,notices=self.setup_picker({'101':1,'102':1})
        env['open_picker'](1,SimpleNamespace(sim=object()))
        dlg=DialogFactory.dialogs[0]
        dlg.click(False,(101,102))
        dlg.click(True,(101,102))
        self.assertEqual(store.saved,0)

    def test_stale_roster_or_disabled_management_blocks_write(self):
        env,store,settings,notices=self.setup_picker({'101':3,'102':3})
        env['open_picker'](3,SimpleNamespace(sim=object()))
        settings.active=False
        DialogFactory.dialogs[0].click(True,(101,102))
        self.assertEqual(store.saved,0)
        self.assertTrue(notices)

    def test_class3_error_notice_is_now_explained(self):
        source=(Path(__file__).resolve().parents[1]/
            'src/m34_settings/mhs34_settings_ui.py').read_text()
        self.assertIn('Classe 3 non disattivata',source)
        self.assertTrue("_settings_notice(" in source or "_warning(actor,str(exc))" in source)

if __name__=='__main__':
    unittest.main()
