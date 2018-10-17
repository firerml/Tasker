import unittest

import messenger


class SlashCommandTest(unittest.TestCase):

    def test_valid_messages_get_correct_responses(self):
        expected_response = {
            'assignee': {'id': 'U1234', 'username': 'mike', 'name_code': '<@U1234|mike>'},
            'task': 'order lunch'
        }

        self.assertEquals(expected_response, messenger._parse_assign_message('<@U1234|mike> to order lunch'))
        self.assertEquals(expected_response, messenger._parse_assign_message('<@U1234|mike> order lunch'))
        self.assertEquals(expected_response, messenger._parse_assign_message('blah blah <@U1234|mike> to order lunch'))

        expected_response['assignee'] = {'id': 'U1234', 'username': 'Mike Firer', 'name_code': '<@U1234|Mike Firer>'}
        self.assertEquals(expected_response, messenger._parse_assign_message('<@U1234|Mike Firer> to order lunch'))
        self.assertEquals(expected_response, messenger._parse_assign_message('<@U1234|Mike Firer> order lunch'))
        self.assertEquals(
            expected_response, messenger._parse_assign_message('blah blah <@U1234|Mike Firer> to order lunch')
        )

    def test_invalid_messages_return_empty(self):
        self.assertEquals({}, messenger._parse_assign_message('order lunch'))
        self.assertEquals({}, messenger._parse_assign_message('order lunch to <@U1234|mike>'))
        self.assertEquals({}, messenger._parse_assign_message('order lunch to <@U1234|Mike Firer>'))
        self.assertEquals({}, messenger._parse_assign_message('<@U1234|mike>blahblah to order lunch'))
