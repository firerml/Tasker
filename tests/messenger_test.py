from unittest.mock import MagicMock, patch
from unittest import TestCase

from messenger import Messenger


class MessengerTest(TestCase):

    def setUp(self):

        def fake_api_call(method, types=None, attachments=None, channel=None, text=None):
            if method == 'conversations.list':
                return {'ok': True, 'channels': [{'user': '456', 'id': 'C456'}, {'user': '123', 'id': 'C123'}]}
            if method == 'chat.postMessage':
                return {'ok': True}

        self.slack_client = MagicMock()
        self.slack_client.api_call.side_effect = fake_api_call

        self.db = MagicMock()
        self.db.add_task.return_value = True
        self.messenger = Messenger(self.db, self.slack_client)

    def test_fulfill_user_intent_with_assign_input(self):
        with patch.object(self.messenger, 'assign_task') as assign_task_mock:
            with patch.object(self.messenger, 'get_assigned_tasks') as get_assigned_tasks_mock:
                assign_task_mock.return_value = 'assign text'
                get_assigned_tasks_mock.return_value = ('tasks text', ['a1'])

                user_id = '123'
                calls_count = 0
                for message in ['assign @mfirer to order lunch', 'assign blah', 'assign', 'ASSIGN']:
                    calls_count += 1
                    res_text, attachments = self.messenger.fulfill_user_intent(message, user_id)

                    self.assertEqual('assign text', res_text)
                    self.assertEqual([], attachments)
                    self.assertEqual(calls_count, len(assign_task_mock.mock_calls))
                    self.assertEqual((message, user_id), assign_task_mock.mock_calls[-1][1])
                    self.assertFalse(get_assigned_tasks_mock.called)

    def test_fulfill_user_intent_with_get_tasks_input(self):
        with patch.object(self.messenger, 'assign_task') as assign_task_mock:
            with patch.object(self.messenger, 'get_assigned_tasks') as get_assigned_tasks_mock:
                assign_task_mock.return_value = 'assign text'
                get_assigned_tasks_mock.return_value = ('tasks text', ['a1'])

                user_id = '123'
                calls_count = 0
                for message in ['tasks', 'see tasks', 'see all tasks', 'TASKS', 'SEE TASKS', 'SEE ALL TASKS']:
                    calls_count += 1
                    res_text, attachments = self.messenger.fulfill_user_intent(message, user_id)

                    self.assertEqual('tasks text', res_text)
                    self.assertEqual(['a1'], attachments)
                    self.assertEqual(calls_count, len(get_assigned_tasks_mock.mock_calls))
                    self.assertEqual((user_id,), get_assigned_tasks_mock.mock_calls[-1][1])
                    self.assertFalse(assign_task_mock.called)

    def test_fulfill_user_intent_with_invalid_input(self):
        with patch.object(self.messenger, 'assign_task') as assign_task_mock:
            with patch.object(self.messenger, 'get_assigned_tasks') as get_assigned_tasks_mock:
                assign_task_mock.return_value = 'assign text'
                get_assigned_tasks_mock.return_value = ('tasks text', ['a1'])

                user_id = '123'
                for message in ['blah', 'see', 'see all']:
                    res_text, attachments = self.messenger.fulfill_user_intent(message, user_id)

                    self.assertEqual(self.messenger.ERROR_WITH_HINT_TEXT, res_text)
                    self.assertEqual([], attachments)
                    self.assertFalse(get_assigned_tasks_mock.called)
                    self.assertFalse(assign_task_mock.called)

    def test_assign_task_happy_path(self):
        # TODO: Check all possibilities for valid assign messages in a for loop like in above tests.
        res_text = self.messenger.assign_task('assign <@123> to order lunch', '456')
        self.assertEqual("Great! I'll tell <@123> to order lunch.", res_text)
        self.assertEqual((('conversations.list',), {'types': 'im'}), self.slack_client.api_call.mock_calls[-2][1:])
        text_for_assignee = 'Hi! <@456> just assigned this task to you:\n> order lunch'
        self.assertEqual(
            (('chat.postMessage',), {'attachments': None, 'channel': 'C123', 'text': text_for_assignee}),
            self.slack_client.api_call.mock_calls[-11][1:]
        )

    # TODO: Tests for every logical path: invalid messages, no channel id, db write failed, and assigner == assignee.
