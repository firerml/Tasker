import json

from flask import Flask, Response, request

from db import Database, DB_URL
from messenger import Messenger


app = Flask(__name__)


messenger = Messenger(Database(DB_URL))
# TODO: Token validation on all endpoints.


@app.route('/events', methods=['POST'])
def events():
    message_type = request.json['type']
    # Initial verification of this endpoint.
    if message_type == 'url_verification':
        return Response(request.json['challenge'])
    # All other events.
    elif message_type == 'event_callback':
        event = request.json['event']
        # A message not posted by the bot.
        # TODO: Verify the channel is the bot's DM channel.
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
        if event['callback_id'] == messenger.TASK_COMPLETED_CALLBACK and event['actions']:
            return messenger.complete_task(event)
    return Response()


# TODO: Put endpoints in a separate controller file and just import them before app.run().

if __name__ == '__main__':
    app.run()
