from backend.app.governance_binder_publication.engine import GovernanceBinderPublicationEngine
from backend.app.official_books_archive_certification.state_store import load_state as load_books_state


def main():
    books_state = load_books_state()
    official = (books_state.get('official_releases') or [])[0]
    assert official.get('official_release_id')
    engine = GovernanceBinderPublicationEngine()
    engine.sync_context({'source': 'smoke'})
    registered = engine.register_publication({
        'operator': 'ops',
        'official_release_id': official['official_release_id'],
        'operations': 'ops',
        'compliance': 'compliance',
        'notes': 'smoke registration',
    })
    publication_case_id = registered['publication_case']['publication_case_id']
    assembled = engine.assemble_retrieval_packet({
        'publication_case_id': publication_case_id,
        'assembler': 'records',
        'artifact_count': 5,
    })
    assert assembled['publication_case']['status'] == 'ready_for_publication'
    published = engine.publish_binder({'publication_case_id': publication_case_id, 'approver': 'governance'})
    assert published['status'] == 'published'
    summary = engine.summary()
    assert summary['published_binder_count'] >= 1
    print('QNT50014 smoke passed')


if __name__ == '__main__':
    main()
