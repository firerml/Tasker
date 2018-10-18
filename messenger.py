import os
import re

from flask import jsonify, Response
from slackclient import SlackClient


class Messenger:
    ASSIGN_INTENT = 'assign_intent'
    TASKS_INTENT = 'tasks_intent'

    TASK_COMPLETED_CALLBACK = 'completed'

    USER_REGEX = r'(<@(.+)(?:\|(.+))?>)'
    SEE_TASKS_REGEX = r'(see\s+)?(all\s+)?tasks.*'

    BACKEND_ERROR_MESSAGE = '*Oops!* There was an error on our end. Try again or email firerml@gmail.com for support.'
    # TODO: Make the bot respond to "help" with this message.
    HINT_TEXT = 'Try something like `assign @user to order lunch` or `tasks`'
    ERROR_WITH_HINT_TEXT = f'*Oops!* {HINT_TEXT}'

    ERROR_RESPONSE = Response(BACKEND_ERROR_MESSAGE, status=500)

    APP_TOKEN = os.environ['TASKER_BOT_TOKEN']

    def __init__(self, db, slack_client=SlackClient(APP_TOKEN)):
        self.db = db
        self.slack_client = slack_client

    def fulfill_user_intent(self, message, user_id):
        # TODO Add "or `see tasks for @user`" when that feature is added.
        user_intent = self._get_intent(message)
        attachments = []
        if user_intent == self.ASSIGN_INTENT:
            res_text = self.assign_task(message, user_id)
        elif user_intent == self.TASKS_INTENT:
            res_text, attachments = self.get_assigned_tasks(user_id)
        else:
            res_text = self.ERROR_WITH_HINT_TEXT
        return res_text, attachments

    # TODO: Add functionality to support "assign task to @user"
    # TODO: Add functionality for deadlines: "assign @user to do X by Oct 12"
    def assign_task(self, message, assigner_id):
        message_info = self._parse_assign_message(message)
        if not message_info:
            return self.ERROR_WITH_HINT_TEXT
        assignee_id = message_info['assignee']['id']
        channel_id = self._get_channel_id_for_user_direct_message(message_info['assignee']['id'])
        task = message_info['task']
        if channel_id:
            db_success = self.db.add_task(
                assigner_id=assigner_id,
                assignee_id=message_info['assignee']['id'],
                description=task
            )
            if db_success:
                if assignee_id == assigner_id:
                    return f"Great! I've saved that task for you."
                else:
                    self.post_in_channel(f'Hi! <@{assigner_id}> just assigned this task to you:\n> {task}', channel_id)
                    return f"Great! I'll tell {message_info['assignee']['name_code']} to {task}."
        return self.BACKEND_ERROR_MESSAGE

    def get_assigned_tasks(self, assignee_id):
        tasks = self.db.get_tasks_for_assignee(assignee_id)
        if tasks:
            res_text = 'Here are your assigned tasks.'
            attachments = [
                {
                    'fallback': str(task),
                    'title': str(task),
                    'callback_id': self.TASK_COMPLETED_CALLBACK,
                    'color': '#3AA3E3',
                    'attachment_type': 'default',
                    'actions': [{
                        'name': 'complete',
                        'text': 'Complete',
                        'type': 'button',
                        'value': f'{task.id},{task.assigner_id},{task.description}'
                    }]
                } for task in tasks
            ]
        else:
            res_text = 'No assigned tasks yet! :surfer:'
            attachments = []
        return res_text, attachments

    def complete_task(self, event):
        # TODO: Return 200 immediately and do all of this asyncronously.
        assignee_id = event['user']['id']
        task_id, assigner_id, task_description = event['actions'][0]['value'].split(',')

        # TODO(?): This could be done in an atomic-ish way where if the notifications fail
        # TODO     the delete task is not committed.
        db_success = self.db.delete_task(int(task_id))
        if db_success:
            # Notify assigner of completion (as long as the assigner isn't the assignee!).
            if not assigner_id == assignee_id:
                channel_id = self._get_channel_id_for_user_direct_message(assigner_id)
                if channel_id:
                    self.post_in_channel(f'<@{assignee_id}> has completed this task:\n>{task_description}', channel_id)

            # Update the message to remove that task, by recreating the original message with all of the same tasks
            # except the completed one.
            # Responding to a message_action with a message json updates the message.
            completed_attachment_id = int(event['attachment_id'])
            original_message = event['original_message']
            response = original_message.copy()
            response['attachments'] = []
            for attachment in original_message['attachments']:
                if attachment['id'] != completed_attachment_id:
                    response['attachments'].append(attachment)
            if not response['attachments']:
                response['text'] = 'All done! :sunglasses:'
            return jsonify(response)
        return Response()

    # Returns success boolean.
    def post_in_channel(self, text, channel, attachments=None):
        if channel:
            res = self.slack_client.api_call('chat.postMessage', attachments=attachments, channel=channel, text=text)
            return res['ok']
        return False

    def _get_intent(self, text):
        lowered_text = text.lower().strip()
        if lowered_text.startswith('assign'):
            return self.ASSIGN_INTENT
        elif re.match(self.SEE_TASKS_REGEX, lowered_text, flags=re.IGNORECASE):
            return self.TASKS_INTENT
        else:
            return None

    def _parse_assign_message(self, message):
        match = re.search(self.USER_REGEX, message)
        if not match:
            return {}
        groups = match.groups()
        # groups[2] is the username should we ever need it, but it's not always present.
        user = {'name_code': groups[0], 'id': groups[1]}
        remaining_text = message[match.end():]
        # Remove starting "to" if present and split on whitespace.
        task_tokens = re.sub('^\s*to\s+', '', remaining_text, flags=re.IGNORECASE).split()
        if not task_tokens:
            return {}
        return {'assignee': user, 'task': ' '.join(task_tokens)}

    def _get_channel_id_for_user_direct_message(self, user_id):
        # TODO: This could maybe be cached, and the actual endpoint called if the user is not found.
        res = self.slack_client.api_call('conversations.list', types='im')
        if res['ok']:
            for channel in res['channels']:
                if channel['user'] == user_id:
                    return channel['id']
        return None
