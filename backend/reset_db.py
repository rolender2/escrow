import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import engine, Base
import models

from sqlalchemy import text

print("Dropping all tables...")
Base.metadata.drop_all(bind=engine)

# Explicitly drop enums (Postgres specific)
with engine.connect() as conn:
    conn.execute(text("DROP TYPE IF EXISTS userrole CASCADE;"))
    conn.execute(text("DROP TYPE IF EXISTS escrowstate CASCADE;"))
    conn.execute(text("DROP TYPE IF EXISTS milestonestatus CASCADE;"))
    conn.commit()

print("Creating all tables...")
Base.metadata.create_all(bind=engine)
print("Database reset complete.")
