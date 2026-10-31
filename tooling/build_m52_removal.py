"""M52: preserve M51 DBPF; native multi-removal and class 3 warning."""
import hashlib,importlib.util,json,py_compile,sys,tempfile,zipfile
from pathlib import Path
from tooling.build_m51_bulk_transfer import package_bytes
from tooling.build_m48_single_checkmark import SCRIPTS
from tooling.simdata_release_gate import inspect_bytes

ROOT=Path(__file__).resolve().parents[1]
EXTRA=ROOT/'src/m52_removal/picker.py'
PACKAGE='MHS_M52_RIMOZIONE_MULTIPLA_TEST.package'
SCRIPT='MHS_M52_RIMOZIONE_MULTIPLA_TEST.ts4script'

def release(folder):
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    data=package_bytes()
    report=inspect_bytes(data)
    assert report['status']=='STATIC_GATE_PASSED'
    assert report['category_count']==report['simdata_count']==5
    (folder/PACKAGE).write_bytes(data)
    assert sys.version_info[:2]==(3,7)
    assert importlib.util.MAGIC_NUMBER==bytes((66,13,13,10))
    src=tuple(SCRIPTS)+(EXTRA,)
    assert len(src)==18
    with tempfile.TemporaryDirectory() as temporary:
        with zipfile.ZipFile(str(folder/SCRIPT),'w',zipfile.ZIP_DEFLATED) as z:
            for file in src:
                path=Path(temporary)/(file.name+'c')
                py_compile.compile(str(file),cfile=str(path),doraise=True)
                name=('mhs52_picker.pyc' if file==EXTRA else file.name+'c')
                z.write(str(path),arcname=name)
    return {'status':'MAC_GAME_TEST_REQUIRED',
            'same_package_as_M51':True,
            'sha256':hashlib.sha256(data).hexdigest(),
            'script_modules':18}

if __name__=='__main__':
    assert len(sys.argv)==2
    print(json.dumps(release(sys.argv[1]),indent=2))
