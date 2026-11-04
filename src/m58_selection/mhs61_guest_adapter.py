"""M61B isolated EA guest-list adapter, Python 3.7, NOT attached to runtime.

Safely construct explicit Base Student invitation for ONE verified candidate.
The actual zone/situation manager integration must separately pass a
game-test gate before it can become active.
"""
BASE_SITUATION=277733
BASE_JOB=277894

def build_guest_list(situation,job,sim_id,guest_list_class,guest_info_class,purpose):
    if getattr(situation,'guid64',None)!=BASE_SITUATION:
        raise ValueError('not verified Base Student situation')
    if getattr(job,'guid64',None)!=BASE_JOB:
        raise ValueError('not verified Base Student job')
    if isinstance(sim_id,bool) or not str(sim_id).isdigit() or int(sim_id)<=0:
        raise ValueError('invalid enrolled Sim ID')
    guest_list=guest_list_class(invite_only=True)
    info=guest_info_class.construct_from_purpose(int(sim_id),job,purpose)
    guest_list.add_guest_info(info)
    return guest_list


def create_one_existing_student(manager,situation,job,sim_id,guest_list_class,
                                guest_info_class,purpose):
    """Explicit isolated trial only; caller must enforce school/roster guards.

    Never starts automatically. Manager call is for exactly one validated Sim,
    not a replacement for all 16 classmates.
    """
    guests=build_guest_list(situation,job,sim_id,guest_list_class,
                            guest_info_class,purpose)
    return manager.create_situation(situation,guest_list=guests,user_facing=False)
