import json

from flask import Flask, Response, request

import messenger


app = Flask(__name__)


# TODO: Token validation on all endpoints.

@app.route('/assign', methods=['POST'])
def assign():
    res_text = messenger.assign_task(request.form['text'], request.form['user_id'], "`/assign @user to order lunch`")
    return messenger.respond_to_slash_command(res_text)


@app.route('/tasks', methods=['POST'])
def tasks():
    res_text, attachments = messenger.get_assigned_tasks(request.form['user_id'])
    return messenger.respond_to_slash_command(res_text)


@app.route('/events', methods=['POST'])
def events():
    message_type = request.json['type']
    if message_type == 'url_verification':
        return Response(request.json['challenge'])
    elif message_type == 'event_callback':
        event = request.json['event']
        if event['type'] == 'message' and event.get('subtype') not in {'bot_message', 'message_changed'}:
            res_text, attachments = messenger.fulfill_user_intent(event['text'], event['user'])
            success = messenger.post_in_channel(res_text, event['channel'], attachments=attachments)
            if success:
                return Response()
            else:
                # TODO: Verify if this message is actually shown to the user.
                # TODO  If not, I should just return an empty 200 (Response()).
                return messenger.BACKEND_ERROR_MESSAGE
    return Response()


@app.route('/message_action', methods=['POST'])
def message_action():
    event = json.loads(request.form['payload'])
    # Nested if statements is unnecessary now but is set up for potential additional callback_ids in the future.
    if event['type'] == 'interactive_message':
        if event['callback_id'] == messenger.COMPLETED_CALLBACK and event['actions']:
            return messenger.complete_task(event)
    return Response()


if __name__ == '__main__':
    app.run()
