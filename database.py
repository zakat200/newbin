from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, create_session, scoped_session
from sqlalchemy.pool import StaticPool
#DB_URL ="postgresql+pypostgresql://postgres:zms2003@localhost/payments"
#DB_URL = "postgresql+pypostgresql://postgres:zms2003@localhost/payments"
DB_URL = "sqlite:///test.db"
#ssl_args = {'sslkey': './simple_technology.pem'}
#DB_URL = "postgresql+pypostgresql://postgres:12345678@payments.ciiykuskfnjf.us-east-1.rds.amazonaws.com/payments?sslmode=require"
engine = create_engine(DB_URL, connect_args={'check_same_thread': False}, poolclass=StaticPool)
#engine = create_engine(DB_URL)
conn = engine.connect()
metadata = MetaData()
#session_sql = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
SessionLocal = sessionmaker(autocommit=True, autoflush=False, bind=engine)
Session = scoped_session(SessionLocal)

Base = declarative_base(metadata=metadata )

metadata.create_all(engine)
#Session = SessionLocal()
##Session.commit()