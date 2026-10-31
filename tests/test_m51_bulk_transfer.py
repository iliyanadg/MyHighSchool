"""M51: prove ONE multi-Sim picker commit, X cancel, and source/target cap."""
import ast
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'/'m2_registry'))
from mhs_m2_roster import SchoolRoster,RosterError

from tooling.build_m51_bulk_transfer import package_bytes,SCRIPTS
from tooling.build_m50_filtered_cap import package_bytes as m50_package


class Dialog(object):
    def __init__(self):
        self.rows=[]
        self.callback=None
        self.shown=False
    def add_row(self,row):
        self.rows.append(row)
    def add_listener(self,cb):
        self.callback=cb
    def show_dialog(self):
        self.shown=True
    def click(self,accept,ids=()):
        self.callback(SimpleNamespace(
            accepted=accept,
            get_result_tags=lambda:tuple(ids)))


class DialogFactory(object):
    dialogs=[]
    @classmethod
    def TunableFactory(cls):
        return SimpleNamespace(default=cls._create)
    @classmethod
    def _create(cls,actor,**kwargs):
        picker=Dialog()
        picker.kwargs=kwargs
        cls.dialogs.append(picker)
        return picker


class Store(object):
    def __init__(self,roster):
        self.roster=roster
        self.saved=0
    def load(self,slot):
        return self.roster
    def save(self,slot,new):
        self.roster=new
        self.saved+=1


class M51Tests(unittest.TestCase):
    def setUp(self):
        self.path=ROOT/'src'/'m32_transfer'/'mhs32_transfer_ui.py'

    def test_menu_package_is_binary_identical_to_M50(self):
        self.assertEqual(package_bytes(),m50_package())
        self.assertIn('mhs32_transfer_ui.py',[p.name for p in SCRIPTS])
        self.assertEqual(len(SCRIPTS),17)

    def _env(self,assignments):
        src=self.path.read_text()
        tree=ast.parse(src)
        names=['plan_transfer','open_transfer_picker']
        fns=[node for node in tree.body
             if isinstance(node,ast.FunctionDef) and node.name in names]
        store=Store(SchoolRoster('11',assignments))
        records=[]
        notices=[]
        ids={str(x) for x in assignments}
        class Settings(object):
            def __init__(self):
                self.active=True
            def require_management(self,slot,num):
                if not self.active:
                    raise ValueError('School disabled')
                if num not in (1,2,3):
                    raise ValueError('Invalid class')
        settings=Settings()
        env={
            'SchoolRoster':SchoolRoster,
            'RosterError':RosterError,
            'current_slot':lambda:'11',
            '_STORE':store,'_SETTINGS':settings,
            '_get_actor':lambda interaction:object(),
            'candidate_rows':lambda roster,klass,lookup:[
                SimpleNamespace(sim_id=int(i))
                for i in roster.class_members(klass)],
            '_lookup_sim_info':lambda sid:None,
            'roster_fingerprint':lambda roster:roster.to_json(),
            '_transfer_selection_strategy':lambda max_students:max_students,
            '_transfer_notice':lambda *args:notices.append(args),
            '_transfer_text':lambda message:message,
            'UiSimPicker':DialogFactory,
            'SimPickerRow':lambda sim_id,sel,tag:SimpleNamespace(sim_id=sim_id,tag=tag),
            'teenager_checker':lambda sid:True,
            '_record':lambda *args:records.append(args),
        }
        DialogFactory.dialogs=[]
        exec(compile(ast.Module(body=fns,type_ignores=[]),
                     '<M51 actual transfer UI>',mode='exec'),env)
        return env,store,settings,records,notices

    def test_bulk_transfer_all_students_in_one_checkmark(self):
        env,store,settings,events,notices=self._env({
            '11':1,'12':1,'13':1,'21':2})
        self.assertTrue(env['open_transfer_picker'](1,3,object()))
        self.assertEqual(len(DialogFactory.dialogs),1)
        picker=DialogFactory.dialogs[0]
        self.assertEqual(picker.kwargs['max_selectable'],3)
        self.assertEqual([r.sim_id for r in picker.rows],[11,12,13])
        picker.click(True,(11,12,13))
        self.assertEqual(store.saved,1)
        self.assertEqual(store.roster.class_members(1),[])
        self.assertEqual(store.roster.class_members(3),['11','12','13'])
        self.assertTrue(any('3 studenti trasferiti' in str(x)
                            for x in notices))
        picker.click(True,(11,12,13))
        self.assertEqual(store.saved,1)

    def test_x_cancel_never_saves_even_if_listener_called_twice(self):
        env,store,_,events,notices=self._env({'11':1,'12':1})
        self.assertTrue(env['open_transfer_picker'](1,3,object()))
        picker=DialogFactory.dialogs[0]
        picker.click(False,(11,12))
        picker.click(True,(11,12))
        self.assertEqual(store.saved,0)
        self.assertEqual(store.roster.class_members(1),['11','12'])

    def test_capped_by_target_free_seats(self):
        assignments={str(i):2 for i in range(21,28)}
        assignments.update({'11':1,'12':1,'13':1})
        env,store,settings,events,notices=self._env(assignments)
        self.assertTrue(env['open_transfer_picker'](1,2,object()))
        picker=DialogFactory.dialogs[0]
        self.assertEqual(picker.kwargs['max_selectable'],1)
        picker.click(True,(11,12))
        self.assertEqual(store.saved,0)
        self.assertEqual(store.roster.class_members(1),['11','12','13'])

    def test_stale_roster_refuses_write(self):
        env,store,settings,events,notices=self._env({'11':1,'12':1})
        self.assertTrue(env['open_transfer_picker'](1,3,object()))
        picker=DialogFactory.dialogs[0]
        store.roster=SchoolRoster('11',{'11':1,'12':1,'13':2})
        picker.click(True,(11,12))
        self.assertEqual(store.saved,0)
        self.assertEqual(store.roster.class_members(3),[])

    def test_full_destination_does_not_open_picker(self):
        assignments={str(i):3 for i in range(21,29)}
        assignments['11']=1
        env,store,settings,events,notices=self._env(assignments)
        self.assertFalse(env['open_transfer_picker'](1,3,object()))
        self.assertEqual(DialogFactory.dialogs,[])
        self.assertEqual(store.saved,0)

    def test_disabled_school_after_picker_blocks_commit(self):
        env,store,settings,events,notices=self._env({'11':1,'12':1})
        self.assertTrue(env['open_transfer_picker'](1,3,object()))
        settings.active=False
        DialogFactory.dialogs[0].click(True,(11,12))
        self.assertEqual(store.saved,0)


if __name__=='__main__':
    unittest.main()
