from datetime import datetime
import os
from unittest import TestCase
from unittest.mock import patch

from db import Database, Task


TEST_DB_FILE = 'tasker_test.db'
TEST_DB_URL = f'sqlite:///{TEST_DB_FILE}'

user1 = 'u1'
user2 = 'u2'

default_timestamp = datetime(2018, 10, 31, 12, 5, 30)


class DBTestCase(TestCase):
    def setUp(self):
        with patch('db.datetime') as mock_datetime:
            mock_datetime.now.return_value = default_timestamp
            self.DB = Database(TEST_DB_URL)
            session = self.DB.sessionmaker()
            session.add(Task(assigner_id=user1, assignee_id=user2, description='order lunch'))
            session.add(Task(assigner_id=user1, assignee_id=user2, description='eat lunch'))
            session.commit()

    def tearDown(self):
        os.remove(TEST_DB_FILE)

    def test_get_tasks_for_assignee(self):
        tasks = self.DB.get_tasks_for_assignee(user1)
        self.assertEqual(0, len(tasks))

        tasks = self.DB.get_tasks_for_assignee(user2)
        self.assertEqual(2, len(tasks))

        self.assertEqual(1, tasks[0].id)
        self.assertEqual(user1, tasks[0].assigner_id)
        self.assertEqual(user2, tasks[0].assignee_id)
        self.assertEqual('order lunch', tasks[0].description)
        self.assertEqual(default_timestamp, tasks[0].created_timestamp)
        self.assertEqual('order lunch (from <@u1> on Oct 31)', str(tasks[0]))

        self.assertEqual(2, tasks[1].id)
        self.assertEqual(user1, tasks[1].assigner_id)
        self.assertEqual(user2, tasks[1].assignee_id)
        self.assertEqual('eat lunch', tasks[1].description)
        self.assertEqual(default_timestamp, tasks[1].created_timestamp)
        self.assertEqual('eat lunch (from <@u1> on Oct 31)', str(tasks[1]))

    def test_add_task(self):
        with patch('db.datetime') as mock_datetime:
            mock_datetime.now.return_value = default_timestamp
            self.DB.add_task(assigner_id=user2, assignee_id=user1, description='my task')
        saved_task = self.DB.sessionmaker().query(Task).filter(Task.description == 'my task').one()

        self.assertEqual(3, saved_task.id)
        self.assertEqual(user2, saved_task.assigner_id)
        self.assertEqual(user1, saved_task.assignee_id)
        self.assertEqual('my task', saved_task.description)
        self.assertEqual(default_timestamp, saved_task.created_timestamp)
        self.assertEqual('my task (from <@u2> on Oct 31)', str(saved_task))

    def test_delete_task(self):
        self.DB.delete_task(1)
        tasks = self.DB.sessionmaker().query(Task).all()
        self.assertEqual(1, len(tasks))
        self.assertEqual('eat lunch', tasks[0].description)
