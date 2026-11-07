"""One lifecycle owner for the unified menu and M148-derived controller.

No saved-game writes, new situations or parallel attendance controller.
Use the same zone-loaded hook already exercised by the project's M55 code.
Loading directly into an ongoing school day refuses installation.
"""
_STATUS='NOT_INITIALIZED'
_HOOK=None


def settings_message(status):
    """Keep technical diagnostics out of the normal settings notification."""
    text=str(status)
    if text=='DISABLED_REGISTRY_PRESERVED':
        return 'Gestione disattivata. Iscrizioni e personale sono conservati.'
    if 'ACTIVATION_REQUIRES_HOME' in text:
        return 'Attiva la gestione da casa: la giornata scolastica in corso resta invariata.'
    if 'BLOCKED' in text or 'NON ATTIVA' in text or 'BLOCCATA' in text:
        if any(code in text for code in ('CORE','EIGHT','classi','Registro')):
            return ('Frequenza non attivata. Completa due classi da otto studenti '
                    'e assegna i cinque ruoli speciali. I dati sono conservati.')
        return ('Frequenza personalizzata non attivata: le regole scolastiche '
                'caricate non sono supportate. I dati sono conservati.')
    return ('Impostazioni salvate. La gestione usa le classi e i ruoli scelti; '
            'le modifiche al gruppo scolastico valgono dalla prossima giornata.')


def refresh(reload=False):
    global _STATUS
    try:
        import services
        import mhs145_classroom_controller as controller
        from mhs_school_session import session_decision
        slot=str(controller.current_slot(allow_travel=True))
        settings=controller.SettingsStore(controller.FOLDER).load(slot)
        runtime=controller._RUNTIME
        zone,schedule=controller.zone_schedule()
        school=schedule in controller.SCHOOL_SCHEDULES
        key=controller.current_school_day(slot)
        if runtime is not None and runtime.slot!=slot:
            if not runtime.stop():
                _STATUS='RESTORE_BLOCKED: '+runtime.error
                return _STATUS
            controller._RUNTIME=None
            runtime=None
        action,reason=session_decision(
            runtime.school_day if runtime is not None else None,
            key,settings.active,school,reload=bool(reload))
        if (action == 'RESET' and reason == 'NEW_SCHOOL_DAY' and
                school and runtime is not None):
            # The hook is already owned by this controller. A school arrival
            # on the next day must reset only its per-day receipts, not
            # uninstall it mid-zone and require another activation from home.
            # begin_school_day validates the saved 2x8 roster before touching
            # any EA situation; no native situation is created or cancelled.
            try:
                if runtime.begin_school_day(key) is not True:
                    raise ValueError('NEW_SCHOOL_DAY_NOT_READY')
            except Exception as exc:
                runtime.school_ready=False
                _STATUS='NEW_SCHOOL_DAY_BLOCKED: '+type(exc).__name__
                return _STATUS
        # M154: a genuine EA zone load at HOME is not a request to disable
        # the already verified MHS session. Preserve controller ownership,
        # saved roster and its single school-arrival watcher across the
        # school -> home -> next school-day sequence. M153's verified slot
        # anchor is required above; changed saves/households fail closed.
        # Class adapters remain scoped by runtime.in_school() and therefore
        # do not alter non-school interactions while the owner is retained.
        # Reset native school situations ONLY when entering the new school
        # day, not while returning home from yesterday's day.
        if (not school and runtime is not None and runtime.active and
                settings.active and (
                    action in ('KEEP','START') or
                    (action=='RESET' and reason=='NEW_SCHOOL_DAY'))):
            controller._m141_start_watcher(runtime)
            _STATUS='HOME_SESSION_STANDBY_NEXT_SCHOOL_DAY'
            return _STATUS
        elif action in ('STOP','RESET') and runtime is not None:
            if not runtime.stop():
                _STATUS='RESTORE_BLOCKED: '+runtime.error
                return _STATUS
            controller._RUNTIME=None
            runtime=None
        if not settings.active:
            _STATUS='DISABLED_REGISTRY_PRESERVED'
            return _STATUS
        if school:
            if runtime is None:
                _STATUS='ACTIVATION_REQUIRES_HOME_NEXT_SCHOOL_DAY'
                return _STATUS
            if not controller._install_school_adapters(runtime):
                reason=(runtime.m145_patch_result or runtime.m140_patch_result or {}).get('reason')
                _STATUS='CLASSROOM_COMPATIBILITY_BLOCKED: '+str(reason)
                try:
                    from mhs34_settings_ui import _settings_notice
                    _settings_notice('MY HIGH SCHOOL - Attivazione bloccata',_STATUS)
                except Exception:
                    pass
                return _STATUS
            controller._m141_start_trace(runtime,'unified_zone_loaded')
            _STATUS='SCHOOL_SESSION_ACTIVE'
            return _STATUS
        # At home, only a disabled/changed/reloaded session removes the old
        # scoped EA adapters; a verified active session remains ready for
        # the next school day, without touching saved enrollment.
        # A fresh controller's hook ownership is transactional and unique.
        if runtime is not None:
            if not runtime.stop():
                _STATUS='RESTORE_BLOCKED: '+runtime.error
                return _STATUS
            controller._RUNTIME=None
        _STATUS=controller.arm_m127()
        return _STATUS
    except Exception as exc:
        _STATUS='ACTIVATION_BLOCKED: '+type(exc).__name__+': '+str(exc)[:140]
        return _STATUS


def install(zone_class=None):
    """Preserve the original method/result and avoid duplicate hook install."""
    global _HOOK,_STATUS
    try:
        if zone_class is None:
            from zone import Zone
            zone_class=Zone
        original=getattr(zone_class,'on_loading_screen_animation_finished',None)
        if not callable(original):
            _STATUS='ZONE_CALLBACK_UNAVAILABLE'
            return False
        if getattr(original,'_mhs_classroom_lifecycle',False):
            return True
        def loaded(zone,*args,**kwargs):
            result=original(zone,*args,**kwargs)
            status=refresh()
            if isinstance(status,str) and any(word in status for word in (
                    'BLOCKED','NON ATTIVA','BLOCCATA','REQUIRES_HOME')):
                try:
                    from mhs34_settings_ui import _settings_notice
                    _settings_notice('MY HIGH SCHOOL',settings_message(status))
                except Exception:
                    pass
            return result
        loaded._mhs_classroom_lifecycle=True
        zone_class.on_loading_screen_animation_finished=loaded
        _HOOK=(zone_class,original,loaded)
        _STATUS='ZONE_LIFECYCLE_INSTALLED'
        return True
    except Exception as exc:
        _STATUS='LIFECYCLE_UNAVAILABLE: '+type(exc).__name__
        return False
