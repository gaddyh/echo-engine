from datetime import datetime, timezone
import pytest
from echo_engine import Message, LocalInteraction, MappingDraft, InteractionResolver, InteractionStore


def message(i, sender='a', reply=None):
    return Message(id=i, chat_id='group', sender_id=sender, sent_at=datetime(2026, 10, 15, tzinfo=timezone.utc), text=i, reply_to_message_id=reply)


def local(key, ids, participants=('a',)):
    return LocalInteraction(local_key=key, message_ids=ids, topic=key, summary=key, participants=list(participants))


def test_interleaved_threads_separate_and_replay_stable():
    store=InteractionStore(); resolver=InteractionResolver(store)
    messages=[message('m1'), message('m2'), message('m3', 'b'), message('m4')]
    draft=MappingDraft(interactions=[local('meet',['m1','m2','m4']), local('other',['m3'],('b',))])
    first=resolver.resolve(messages,draft)
    assert len(first.interactions)==2
    assert first.interactions[0].id != first.interactions[1].id
    again=resolver.resolve(messages,draft)
    assert [x.id for x in first.interactions] == [x.id for x in again.interactions]
    assert len(store.list('group'))==2


def test_new_message_overlapping_evidence_extends_existing():
    resolver=InteractionResolver(InteractionStore())
    old=resolver.resolve([message('m1')], MappingDraft(interactions=[local('first',['m1'])])).interactions[0]
    new=resolver.resolve([message('m1'),message('m2')],MappingDraft(interactions=[local('updated',['m1','m2'])])).interactions[0]
    assert old.id==new.id and new.message_ids==['m1','m2']


def test_non_overlapping_messages_do_not_merge_automatically():
    resolver=InteractionResolver(InteractionStore())
    first=resolver.resolve([message('m1')],MappingDraft(interactions=[local('a',['m1'])])).interactions[0]
    second=resolver.resolve([message('m2')],MappingDraft(interactions=[local('a',['m2'])])).interactions[0]
    assert first.id!=second.id


def test_ambiguous_bridge_remains_unresolved():
    resolver=InteractionResolver(InteractionStore())
    resolver.resolve([message('m1'),message('m2')],MappingDraft(interactions=[local('a',['m1']),local('b',['m2'])]))
    result=resolver.resolve([message('m1'),message('m2')],MappingDraft(interactions=[local('bridge',['m1','m2'])]))
    assert result.unresolved_local_keys==['bridge']
    assert len(result.interactions)==0


def test_unknown_message_rejected():
    resolver=InteractionResolver(InteractionStore())
    with pytest.raises(ValueError,match='unknown evidence'):
        resolver.resolve([message('m1')],MappingDraft(interactions=[local('a',['m404'])]))


def test_missing_message_rejected():
    resolver=InteractionResolver(InteractionStore())
    with pytest.raises(ValueError, match='every input'):
        resolver.resolve([message('m1'),message('m2')], MappingDraft(interactions=[local('a',['m1'])]))


def test_unassigned_supported():
    resolver=InteractionResolver(InteractionStore())
    r=resolver.resolve([message('m1')],MappingDraft(interactions=[],unassigned_message_ids=['m1']))
    assert r.unassigned_message_ids==['m1']
