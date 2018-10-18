from datetime import datetime
import logging
import os

from sqlalchemy import Column, create_engine, Index, Integer, sql, String, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DB_URL = os.environ.get('DATABASE_URL', 'sqlite:///tasker.db')
Base = declarative_base()


class Task(Base):

    # Seems unnecessary, but doing this makes the timestamp mockable.
    def get_datetime(self):
        return datetime.now()

    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True)
    assigner_id = Column(String(length=40), nullable=False, index=True)
    assignee_id = Column(String(length=40), nullable=False, index=True)
    description = Column(String, nullable=False)
    created_timestamp = Column(TIMESTAMP(timezone=True), default=get_datetime)
    __table_args__ = (Index('assignee_id', assignee_id.desc()),)

    def __repr__(self):
        return f"{self.description} (from <@{self.assigner_id}> on {self.created_timestamp.strftime('%b %-d')})"

    def __str__(self):
        return self.__repr__()


class Database:
    def __init__(self, db_url):
        engine = create_engine(db_url)
        self.sessionmaker = sessionmaker(bind=engine)

        # Create Task table if it does not exist.
        if not engine.dialect.has_table(engine, Task.__tablename__):
            Base.metadata.create_all(engine)

    def get_tasks_for_assignee(self, assignee_id):
        return self.sessionmaker() \
            .query(Task) \
            .filter(Task.assignee_id == assignee_id) \
            .order_by(Task.created_timestamp) \
            .all()

    # Returns success boolean
    def add_task(self, assigner_id, assignee_id, description):
        session = self.sessionmaker()
        session.add(
            Task(
                assigner_id=assigner_id,
                assignee_id=assignee_id,
                description=description
            )
        )
        return self._commit(session)

    def delete_task(self, task_id):
        session = self.sessionmaker()
        session.query(Task).filter(Task.id == task_id).delete()
        return self._commit(session)

    def _commit(self, session):
        try:
            session.commit()
            return True
        except Exception as e:
            logging.error(e)
            session.rollback()
            return False
