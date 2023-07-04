from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float, BLOB
from sqlalchemy.types import Date
from database import Base,  metadata, engine



class Objects(Base):
    """Data model for coins and stocks."""
    __tablename__= "stocks-and-coins"
    id = Column(Integer, primary_key=True, unique=True)
    type = Column(String)
    name = Column(String, unique = True)
    symbol = Column(String, unique=True)
    logo = Column(String)
    change = Column(Float)
    price = Column(Integer)

class History(Base):
    __tablename__="history"
    id = Column(Integer, primary_key=True, unique=True)
    type = Column(String)
    symbol = Column(String)
    price = Column(Integer)
    timestamp = Column(String)
    counter = Column(Integer)

class Users(Base):
    __tablename__="users"
    id = Column(Integer, primary_key=True, unique=True)
    public_id = Column(String, unique=True)
    email = Column(String, unique=True)
    phone = Column(String, unique=True)
    name = Column(String, default = "Имя")
    second_name = Column(String, default="Фамилия")
    country = Column(String, )
    index = Column(Integer, default = 25473)
    city = Column(String, default = 'Нью-Йорк')
    address = Column(String, default="50, Old Street, Brooklyn")
    current_address = Column(String, default="50, Old Street, Brooklyn")
    birth = Column(String)
    referl = Column(String)
    password = Column(String)
    second_password = Column(String, nullable=True)
    balance = Column(Float, default=0)
    verificated = Column(Boolean, default=False)
    banned = Column(Boolean, default=False)
    admin = Column(Boolean, default=False)

class Transactions(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, unique=True)
    pub_id = Column(String, unique=True)
    user = Column(String)
    date = Column(DateTime)
    result = Column(Float)
    bal = Column(Float)
    status = Column(String)

class Deals(Base):
    __tablename__ = "deals"
    id = Column(Integer, primary_key=True)
    user = Column(String)
    symbol = Column(String)
    type = Column(String)
    sum = Column(Float)
    course = Column(Float)
class Rooms(Base):
    __tablename__ = "rooms"
    count=Column(Integer, primary_key=True)
    id=Column( String, unique=True)
    name=Column(String, nullable=False)
    started=Column(DateTime, nullable=False)
    closed=Column(Boolean)

class Messages(Base):
    __tablename__ = "messages"
    _id=Column( Integer, primary_key=True)
    content=Column( String, nullable=False)
    timestamp=Column( String, nullable=False)
    roomId=Column(String, nullable=False)
    senderId=Column( String, nullable=False)
    date = Column(String)


class Files(Base):
    __tablename__ = "files"
    id = Column(Integer, primary_key=True)
    msg = Column(Integer)
    name = Column(String)
    blob = Column(BLOB)
    extension=Column(String)
    localUrl = Column(String)
    type = Column(String)
    size = Column(Integer)
    path = Column(String)

class User_Rooms(Base):
    __tablename__="user_rooms"
    id = Column(Integer, primary_key=True)
    user = Column(String)
    room = Column(String)
    admin = Column(Boolean)

class Contracts(Base):
    __tablename__="contracts"
    id = Column(Integer, primary_key=True)
    user = Column(String)
    name = Column(String)
    date = Column(String)
    path=Column(String, unique=True)

class Orders(Base):
    __tablename__="orders"
    id = Column(Integer, primary_key=True)
    user = Column(String)
    amount= Column(Integer)
    system = Column(String)

class ChangePassRequests(Base):
    __tablename__="change_pass_requests"
    id = Column(Integer, primary_key=True)
    passw = Column(String)
    email = Column(String, unique=True)
    code = Column(String, unique=True)

class Verification(Base):
    __tablename__="verification"
    id = Column(Integer, primary_key=True)
    address=Column(String)
    name=Column(String)
    country=Column(String)
    phone=Column(String, unique=True)
    number=Column(String)
    second_name = Column(String)
    type = Column(String)
    user = Column(String, unique=True)

class VerifyFiles(Base):
    __tablename__="verify_files"
    id = Column(Integer, primary_key=True)
    ver_id = Column(Integer)
    filepath=Column(String)
    name=Column(String)

class PaymentRequests(Base):
    __tablename__="paymentrequests"
    id = Column(Integer, primary_key=True)
    amount = Column(Float)
    public_id = Column(String)
    address = Column(String)
    transaction=Column(String)
    system = Column(String)

metadata.create_all(engine)