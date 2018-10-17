import logging
import os

from sqlalchemy import Column, create_engine, Index, Integer, sql, String, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DB_URL = os.environ.get('DATABASE_URL', 'sqlite:///tasker.db')
Base = declarative_base()


class Task(Base):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True)
    assigner_id = Column(String(length=40), nullable=False, index=True)
    assignee_id = Column(String(length=40), nullable=False, index=True)
    description = Column(String, nullable=False)
    created_timestamp = Column(TIMESTAMP(timezone=True), server_default=sql.func.now())
    __table_args__ = (Index('assigner_id__assignee_id', assigner_id.desc(), assignee_id.desc()),)

    def __repr__(self):
        return f"{self.description} (from <@{self.assigner_id}> on {self.created_timestamp.strftime('%b %-d')})"

    def __str__(self):
        return self.__repr__()


class Database:
    def __init__(self):
        engine = create_engine(DB_URL)
        self.sessionmaker = sessionmaker(bind=engine)

        # Create Task table if it does not exist.
        if not engine.dialect.has_table(engine, Task.__tablename__):
            Base.metadata.create_all(engine)

    def commit(self, session):
        try:
            session.commit()
            return True
        except Exception as e:
            logging.error(e)
            session.rollback()
            return False

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
        return self.commit(session)

    def delete_task(self, task_id):
        session = self.sessionmaker()
        session.query(Task).filter(Task.id == task_id).delete()
        return self.commit(session)


DB = Database()
