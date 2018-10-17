import os
import re

from db import DB
from flask import jsonify, Response
from slackclient import SlackClient


ASSIGN_INTENT = 'assign_intent'
TASKS_INTENT = 'tasks_intent'

USERTAG_REGEX = r'(<@(.+)(?:\|(.+))?>)'
SEE_TASKS_REGEX = r'(see\s+)?(all\s+)?tasks.*'

COMPLETED_CALLBACK = 'completed'

BACKEND_ERROR_MESSAGE = '*Oops!* There was an error on our end. Try again or email firerml@gmail.com for support.'
ERROR_RESPONSE = Response(BACKEND_ERROR_MESSAGE, status=500)

APP_TOKEN = os.environ['TASKER_BOT_TOKEN']

slack_client = SlackClient(APP_TOKEN)


def assign_task(message, assigner_id, retry_suggestion):
    message_info = _parse_assign_message(message)
    if not message_info:
        return f"*Oops!* That didn't work. Try something like {retry_suggestion}"
    assignee_id = message_info['assignee']['id']
    channel_id = get_channel_id_for_user_direct_message(message_info['assignee']['id'])
    task = message_info['task']
    if channel_id:
        db_success = DB.add_task(
            assigner_id=assigner_id,
            assignee_id=message_info['assignee']['id'],
            description=task
        )
        if db_success:
            if assignee_id == assigner_id:
                return f"Great! I've saved that task for you."
            else:
                post_in_channel(f'Hi! <@{assigner_id}> just assigned this task to you:\n> {task}', channel_id)
                return f"Great! I'll tell {message_info['assignee']['name_code']} to {task}."
    return BACKEND_ERROR_MESSAGE


def _parse_assign_message(message):
    match = re.search(USERTAG_REGEX, message)
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


def get_assigned_tasks(assignee_id):
    tasks = DB.get_tasks_for_assignee(assignee_id)
    if tasks:
        res_text = 'Here are your assigned tasks.'
        attachments = [
            {
                'fallback': str(task),
                'title': str(task),
                'callback_id': COMPLETED_CALLBACK,
                'color': '#3AA3E3',
                'attachment_type': 'default',
                'actions': [
                    {
                        'name': 'complete',
                        'text': 'Complete',
                        'type': 'button',
                        'value': f'{task.id},{task.assigner_id},{task.description}'
                    }
                ]
            } for task in tasks
        ]
    else:
        res_text = 'No assigned tasks yet! :surfer:'
        attachments = []
    return res_text, attachments


def fulfill_user_intent(message, user_id):
    assign_suggestion = '`assign @user to order lunch`'
    # TODO Add "or `see tasks for @user`" when that feature is added.
    help_text = f'Try something like {assign_suggestion} or `see tasks`'
    user_intent = _get_intent(message)
    attachments = []
    if user_intent == ASSIGN_INTENT:
        res_text = assign_task(message, user_id, assign_suggestion)
    elif user_intent == TASKS_INTENT:
        res_text, attachments = get_assigned_tasks(user_id)
    else:
        res_text = f'*Oops!* {help_text}'
    return res_text, attachments


def _get_intent(text):
    lowered_text = text.lower().strip()
    if lowered_text.startswith('assign'):
        return ASSIGN_INTENT
    elif re.match(SEE_TASKS_REGEX, lowered_text, flags=re.IGNORECASE):
        return TASKS_INTENT
    else:
        return None


def respond_to_slash_command(text):
    return jsonify({'text': text, 'response_type': 'ephemeral'})


def get_channel_id_for_user_direct_message(user_id):
    res = slack_client.api_call('conversations.list', types='im')
    if res['ok']:
        for channel in res['channels']:
            if channel['user'] == user_id:
                return channel['id']
    return None


# Returns success boolean.
def post_in_channel(text, channel, attachments=None):
    if channel:
        res = slack_client.api_call('chat.postMessage', attachments=attachments, channel=channel, text=text)
        return res['ok']
    return False


def complete_task(event):
    # TODO: Return 200 immediately and do all of this asyncronously.
    assignee_id = event['user']['id']
    task_id, assigner_id, task_description = event['actions'][0]['value'].split(',')

    db_success = DB.delete_task(int(task_id))
    if db_success:
        # Notify assigner of completion (as long as the assigner isn't the assignee!).
        if not assigner_id == assignee_id:
            channel_id = get_channel_id_for_user_direct_message(assigner_id)
            if channel_id:
                post_in_channel(f'<@{assignee_id}> has completed this task:\n>{task_description}', channel_id)
        # Update the message to cross it out and remove the button.
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
