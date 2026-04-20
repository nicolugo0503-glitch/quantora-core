from backend.app.official_books_archive_certification.engine import OfficialBooksArchiveCertificationEngine
from backend.app.period_close_distribution_ledger.state_store import load_state as load_period_state


def main():
    period_state = load_period_state()
    closed = (period_state.get('closed_periods') or [])[0]
    assert closed.get('period_close_id')
    engine = OfficialBooksArchiveCertificationEngine()
    engine.sync_context({'source':'smoke'})
    registered = engine.register_release({
        'operator':'ops',
        'period_close_id': closed['period_close_id'],
        'controller':'controller',
        'operations':'ops',
        'notes':'smoke registration',
    })
    rid = registered['books_release']['books_release_id']
    certified = engine.certify_archive({'books_release_id': rid, 'certifier':'records', 'artifact_count': 4})
    assert certified['books_release']['status'] == 'ready_for_official_release'
    released = engine.release_official_books({'books_release_id': rid, 'approver':'cfo'})
    assert released['status'] == 'released'
    summary = engine.summary()
    assert summary['official_release_count'] >= 1
    print('QNT50013 smoke passed')


if __name__ == '__main__':
    main()
