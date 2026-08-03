from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import DateTime

from datetime import datetime

from .db import Base


class Conversation(Base):

    __tablename__ = "conversation"

    id = Column(Integer, primary_key=True)

    session_id = Column(String)

    role = Column(String)

    message = Column(Text)

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )