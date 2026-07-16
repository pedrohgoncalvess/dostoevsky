import os
from dotenv import load_dotenv

load_dotenv()

# Ensure we have the DB variables set so run.py works
os.environ["DB_HOST"] = "localhost"
os.environ["DB_PORT"] = "5440"
os.environ["DB_USER"] = "postgres"
os.environ["DB_PASSWORD"] = "postgres"
os.environ["DB_NAME"] = "postgres"

from database.migrations.run import apply_migrations
apply_migrations()
print("Migrations applied!")
