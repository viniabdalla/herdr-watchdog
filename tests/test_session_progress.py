"""Checklist calls below are synthetic protocol controls, not invented real evidence.

Local native histories inspected on 2026-11-17 contain orchestration/Bash records,
but no successful update_plan/TodoWrite/TaskCreate/TaskUpdate pairs. The unrelated
redacted Claude envelope in test_genuine_unrelated_envelope is observed locally.
"""
import json
import unittest
from watchdog_app.session_progress import Checklist


def codex_call(identity='c1', status='in_progress', name='update_plan'):
    return {'type':'response_item','payload':{'type':'function_call','name':name,
        'call_id':identity,'arguments':json.dumps({'plan':[{'step':'Inspect fixtures','status':status},
        {'step':'Verify refresh','status':'pending'}]})}}


def codex_result(identity='c1', output='Plan updated'):
    return {'type':'response_item','payload':{'type':'function_call_output','call_id':identity,'output':output}}


def claude_call(name='TodoWrite', identity='c1', **data):
    return {'type':'assistant','sessionId':'s','uuid':'assistant-'+identity,'message':{'content':[
        {'type':'tool_use','id':identity,'name':name,'input':data or {'todos':[
        {'content':'Inspect fixtures','status':'in_progress','activeForm':'Inspecting fixtures'}]}}]}}


def claude_result(identity='c1', error=False):
    return {'type':'user','sessionId':'s','uuid':'result-'+identity,'message':{'content':[
        {'type':'tool_result','tool_use_id':identity,'content':'Todos have been modified successfully.', 'is_error':error}]}}


class ChecklistTests(unittest.TestCase):
    def test_only_successful_matching_native_calls_change_plan(self):
        plan=Checklist('codex','s')
        plan.feed(codex_result());self.assertEqual(plan.view().state,'no_checklist')
        plan.feed(codex_call());self.assertEqual(plan.view().state,'no_checklist')
        plan.feed(codex_result(output='Error: invalid arguments'));self.assertIsNone(plan.view().total)
        plan.feed(codex_call('c2'));plan.feed(codex_result('c2'))
        view=plan.view();self.assertEqual((view.state,view.done,view.total,view.current),('working',0,2,'Inspect fixtures'))
        plan.feed(codex_call('other',name='exec'));plan.feed(codex_result('other'))
        self.assertEqual(plan.view().total,2)

    def test_completed_steps_empty_plan_and_replayed_call_ids(self):
        plan=Checklist('codex','s');plan.feed(codex_call(status='completed'));plan.feed(codex_result())
        self.assertEqual(plan.view().done,1)
        plan.feed({'type':'event_msg','payload':{'type':'task_started','turn_id':'new'}})
        plan.feed(codex_call());plan.feed(codex_result())
        self.assertIsNone(plan.view().total,'old call replay must not revive the previous turn')
        call=codex_call('empty');call['payload']['arguments']='{"plan":[]}'
        plan.feed(call);plan.feed(codex_result('empty'))
        self.assertEqual(plan.view().state,'no_checklist');self.assertIsNone(plan.view().total)

    def test_new_turn_and_failed_results_never_invent_progress(self):
        plan=Checklist('codex','s');plan.feed(codex_call());plan.feed(codex_result())
        plan.feed({'type':'turn_context','payload':{'turn_id':'next'}})
        self.assertEqual(plan.view().state,'no_checklist')
        plan.feed(codex_call('late'))
        plan.feed({'type':'event_msg','payload':{'type':'task_started','turn_id':'later'}})
        plan.feed(codex_result('late'));self.assertIsNone(plan.view().total)

    def test_malformed_unrelated_and_wrong_source_rows_are_ignored(self):
        plan=Checklist('codex','s')
        for row in ({'payload':[]},{'type':'response_item','payload':None},codex_result(),
                    {'type':'event_msg','payload':{'type':'agent_message','message':'Plan updated'}}):
            plan.feed(row)
        call=codex_call();call['isSidechain']=True;plan.feed(call);plan.feed(codex_result())
        self.assertIsNone(plan.view().total)
        plan.feed({'type':'session_meta','payload':{'id':'another'}})
        plan.feed(codex_call('wrong'));plan.feed(codex_result('wrong'))
        self.assertEqual(plan.view().state,'unavailable')

    def test_pending_calls_and_dedup_memory_are_bounded(self):
        plan=Checklist('codex','s')
        for i in range(5000):plan.feed(codex_call(str(i)))
        self.assertLessEqual(len(plan.pending),128)
        self.assertLessEqual(len(plan.seen),4096)
        plan.feed(codex_result('0'));self.assertIsNone(plan.view().total)
        plan.feed(codex_result('4999'));self.assertEqual(plan.view().total,2)

    def test_claude_todowrite_correlates_result_excludes_sidechain_and_new_prompt(self):
        plan=Checklist('claude','s')
        call=claude_call();call['isSidechain']=True;plan.feed(call);plan.feed(claude_result())
        self.assertIsNone(plan.view().total)
        plan.feed(claude_call(identity='fail'));plan.feed(claude_result('fail',True))
        self.assertIsNone(plan.view().total)
        plan.feed(claude_call(identity='ok'));plan.feed(claude_result('ok'))
        self.assertEqual((plan.view().total,plan.view().current),(1,'Inspect fixtures'))
        plan.feed({'type':'user','sessionId':'s','uuid':'prompt','message':{'content':'Next task'}})
        self.assertIsNone(plan.view().total)
        plan.feed(claude_call(name='TaskCreate',identity='unsupported',subject='Example'))
        plan.feed(claude_result('unsupported'))
        self.assertEqual(plan.view().state,'unsupported')

    def test_genuine_unrelated_envelope_does_not_become_a_checklist(self):
        # Observed Claude 2.1.319 envelope; UUID/text/path redacted, no shape changes.
        plan=Checklist('claude','s')
        plan.feed({'parentUuid':'previous','isSidechain':False,'promptId':'prompt',
            'type':'user','uuid':'result','sourceToolAssistantUUID':'assistant',
            'session_id':'s','sessionId':'s','version':'2.1.319','toolUseResult':{'stdout':'Plan updated','stderr':'','interrupted':False,'isImage':False,'noOutputExpected':False},
            'message':{'role':'user','content':[{'tool_use_id':'bash-call','type':'tool_result',
            'content':'Plan updated','is_error':False}]}})
        self.assertIsNone(plan.view().total)

    def test_code_stdin_and_wrong_namespace_never_act_as_native_checklist(self):
        plan=Checklist('codex','s')
        plan.feed({'type':'response_item','payload':{'type':'custom_tool_call','name':'exec',
            'call_id':'wrapper','input':'await tools.update_plan({plan:[{step:"Fake",status:"completed"}]})'}})
        plan.feed(codex_result('wrapper'))
        call=codex_call('wrong');call['payload']['namespace']='external'
        plan.feed(call);plan.feed(codex_result('wrong'))
        self.assertIsNone(plan.view().total)

    def test_claude_result_in_other_session_cannot_commit_pending_plan(self):
        plan=Checklist('claude','s');plan.feed(claude_call())
        result=claude_result();result['sessionId']='another'
        plan.feed(result);self.assertIsNone(plan.view().total)

    def test_failed_unsupported_task_tool_does_not_erase_a_valid_todo_list(self):
        plan=Checklist('claude','s');plan.feed(claude_call());plan.feed(claude_result())
        plan.feed(claude_call(name='TaskUpdate',identity='bad',taskId='1',status='completed'))
        plan.feed(claude_result('bad',True))
        self.assertEqual(plan.view().total,1)

    def test_malformed_successful_native_schema_is_unsupported_not_zero(self):
        plan=Checklist('codex','s');call=codex_call()
        call['payload']['arguments']='{"plan":[{"text":"Unknown schema"}]}'
        plan.feed(call);plan.feed(codex_result())
        self.assertEqual(plan.view().state,'unsupported');self.assertIsNone(plan.view().total)

    def test_claude_tool_named_like_codex_is_not_a_native_claude_checklist(self):
        plan=Checklist('claude','s')
        plan.feed(claude_call(name='update_plan',plan=[{'step':'Fake','status':'completed'}]))
        result=claude_result();result['message']['content'][0]['content']='Plan updated'
        plan.feed(result);self.assertIsNone(plan.view().total)

    def test_old_turn_attribution_cannot_replace_current_plan(self):
        plan=Checklist('codex','s')
        plan.feed({'type':'turn_context','payload':{'turn_id':'now'}})
        call=codex_call();call['payload']['internal_chat_message_metadata_passthrough']={'turn_id':'old'}
        plan.feed(call);plan.feed(codex_result());self.assertIsNone(plan.view().total)

    def test_user_message_turn_id_resets_plan_without_task_started_record(self):
        plan=Checklist('codex','s');plan.feed(codex_call());plan.feed(codex_result())
        plan.feed({'type':'event_msg','payload':{'type':'user_message','turn_id':'next','message':'New work'}})
        self.assertIsNone(plan.view().total)
