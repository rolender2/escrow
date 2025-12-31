from backend.database import engine, Base
from backend.models import Escrow, Milestone, Evidence

print("Dropping all tables...")
Base.metadata.drop_all(bind=engine)
print("Tables dropped. Restart backend to recreate.")
