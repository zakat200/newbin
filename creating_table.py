from sqlalchemy import create_engine, MetaData, Table, DateTime, Integer, String, Column, Boolean
from database import engine, metadata

messages=Table("files", metadata,
               Column("id", Integer, primary_key=True),
               Column("msg", Integer, nullable=False),
               Column("path", String, nullable=False),
               Column("sender", String, nullable=False),
               Column("read", Boolean))

metadata.create_all(bind = engine, tables=[messages])
exit()