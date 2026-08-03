from .db import engine
from .models import Base


def init_database():

    Base.metadata.create_all(bind=engine)