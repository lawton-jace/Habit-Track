"""
Database Migration Script: Add category_id column to habit table

This migration fixes the schema mismatch where the Habit model has a category_id
column defined in SQLAlchemy, but the actual SQLite database table doesn't have
this column (because the table was created before the categories feature was added).

WHAT THIS SCRIPT DOES:
1. Connects to the SQLite database (instance/habitstreak.db)
2. Checks if the 'category_id' column already exists in the 'habit' table
3. If the column is missing, adds it using ALTER TABLE
4. The column is added as a nullable INTEGER with a foreign key reference to habit_category.id

WHY THIS IS NEEDED:
- SQLAlchemy's db.create_all() only creates NEW tables - it doesn't modify existing ones
- The habit categories feature was added after the initial database creation
- This left the habit table without the category_id column that the code expects

HOW TO RUN:
    python migrate_add_category.py

SAFETY:
- This script is idempotent (safe to run multiple times)
- It checks for column existence before attempting to add it
- All existing data is preserved
- No data is deleted or modified
"""

import sqlite3
import os

# Path to the SQLite database
DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'habitstreak.db')


def column_exists(cursor, table_name, column_name):
    """
    Check if a column exists in a SQLite table.

    SQLite stores table schema information in a system table called 'sqlite_master'.
    We use PRAGMA table_info() to get column metadata for a specific table.
    This returns rows with: (cid, name, type, notnull, dflt_value, pk)
    """
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]  # col[1] is the column name
    return column_name in column_names


def run_migration():
    """
    Execute the migration to add the category_id column.

    DETAILED EXPLANATION OF THE MIGRATION:

    1. We connect to the SQLite database using sqlite3
    2. We check if 'category_id' already exists in 'habit' table
       - If it exists, we skip (makes this script safe to run multiple times)
       - If it doesn't exist, we proceed with the migration
    3. We execute ALTER TABLE to add the new column:
       - Column name: category_id
       - Data type: INTEGER (matches SQLAlchemy's db.Integer)
       - Constraints: REFERENCES habit_category(id) - foreign key relationship
       - The column is nullable by default, which matches the model definition
    4. We commit the transaction to persist the change

    NOTE ON SQLite FOREIGN KEYS:
    SQLite doesn't enforce foreign key constraints by default. The REFERENCES clause
    is included for documentation and compatibility, but SQLite won't prevent invalid
    category_id values unless you run 'PRAGMA foreign_keys = ON' before operations.
    Flask-SQLAlchemy handles referential integrity at the application level.
    """

    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database not found at {DB_PATH}")
        print("Make sure to run the app at least once to create the database.")
        return False

    print(f"Connecting to database: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if the column already exists
        if column_exists(cursor, 'habit', 'category_id'):
            print("SUCCESS: Column 'category_id' already exists in 'habit' table.")
            print("No migration needed - your schema is already up to date!")
            return True

        print("Column 'category_id' not found in 'habit' table.")
        print("Running migration to add the column...")

        # Add the category_id column
        # SQL Breakdown:
        # - ALTER TABLE habit: Modify the 'habit' table structure
        # - ADD COLUMN category_id: Add a new column named 'category_id'
        # - INTEGER: The data type (matches SQLAlchemy db.Integer)
        # - REFERENCES habit_category(id): Foreign key to habit_category table
        cursor.execute("""
            ALTER TABLE habit
            ADD COLUMN category_id INTEGER REFERENCES habit_category(id)
        """)

        conn.commit()

        # Verify the migration worked
        if column_exists(cursor, 'habit', 'category_id'):
            print("SUCCESS: Migration completed!")
            print("Column 'category_id' has been added to the 'habit' table.")

            # Show the updated table schema
            print("\nUpdated 'habit' table schema:")
            cursor.execute("PRAGMA table_info(habit)")
            columns = cursor.fetchall()
            for col in columns:
                cid, name, col_type, notnull, default, pk = col
                nullable = "NOT NULL" if notnull else "NULL"
                primary = "(PK)" if pk else ""
                print(f"  - {name}: {col_type} {nullable} {primary}")

            return True
        else:
            print("ERROR: Migration failed - column was not added.")
            return False

    except sqlite3.Error as e:
        print(f"ERROR: SQLite error occurred: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


if __name__ == '__main__':
    print("=" * 60)
    print("Habit Streak Insurance - Database Migration")
    print("Adding 'category_id' column to 'habit' table")
    print("=" * 60)
    print()

    success = run_migration()

    print()
    if success:
        print("Migration completed successfully!")
        print("You can now use habit categories in your application.")
    else:
        print("Migration failed. Please check the error messages above.")

    print("=" * 60)
