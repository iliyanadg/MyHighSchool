"""M85 diagnostic report, called only from the existing school menu."""
import json
import os
from mhs85_live_snapshot import snapshot

REPORT_NAME='MHS_M85_PRESENZE_RUOLI_EA.json'

def capture_status(folder):
    try:
        import services
        from sims.sim_info_types import Age, Species
        import mhs57_filter_runtime
        from mhs55_attendance_core import situation_guid
        manifest=mhs57_filter_runtime._manifest()
        if manifest is None:
            return {'status':'MHS inactive'}
        simmgr=services.sim_info_manager()
        mgr=services.get_zone_situation_manager()
        if simmgr is None or mgr is None:
            return {'status':'EA school services not ready'}
        report=snapshot(manifest,simmgr.get_all(),mgr,
                        Age.TEEN,Species.HUMAN,situation_guid)
        if report.get('status')=='observed':
            os.makedirs(folder,exist_ok=True)
            path=os.path.join(folder,REPORT_NAME)
            tmp=path+'.tmp'
            with open(tmp,'w',encoding='utf-8') as fp:
                json.dump(report,fp,indent=2,sort_keys=True)
            os.replace(tmp,path)
        return report
    except Exception as exc:
        return {'status':'unavailable: '+type(exc).__name__}

def short_line(result):
    if result.get('status')!='observed':
        return 'M85: diagnostica non disponibile ({})'.format(result.get('status','?'))
    c=result
    by_class=c['in_ea_school_situations_per_class']
    first=by_class[0] if len(by_class)>0 else 0
    second=by_class[1] if len(by_class)>1 else 0
    return ('M85: iscritti sul lotto {}/{}, in situazione EA {}/{}. '
            'C1:{} C2:{} (NON significa seduti).'.format(
                c['registered_on_lot'],c['registered'],
                c['registered_in_ea_school_situations'],c['registered'],
                first,second))
