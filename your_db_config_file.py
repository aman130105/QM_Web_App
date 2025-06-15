import os
import psycopg2

# Get the database URL from the environment variable
DATABASE_URL = os.environ.get("DATABASE_URL")

# Establish a connection to the database
conn = psycopg2.connect(DATABASE_URL)

# No changes needed, already using DATABASE_URL from environment