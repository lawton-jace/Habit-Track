"""
Database Migration Script: Add notification_frequency column to habit table

This migration adds a notification_frequency column to the habit table to support
configurable reminder notifications for each habit.

WHAT THIS SCRIPT DOES:
1. Connects to the SQLite database (instance/habitstreak.db)
2. Checks if the 'notification_frequency' column already exists in the 'habit' table
3. If the column is missing, adds it using ALTER TABLE with a default value of 'daily'
4. Updates any existing rows with NULL values to use the default 'daily' setting

NOTIFICATION FREQUENCY OPTIONS:
- 'multiple_daily': Reminders multiple times per day
- 'daily': Once daily reminder (default)
- 'weekly': Weekly summary reminder
- 'off': No reminders

HOW TO RUN:
    python migrate_add_notification.py

SAFETY:
- This script is idempotent (safe to run multiple times)
- It checks for column existence before attempting to add it
- All existing data is preserved
- Existing habits get the 'daily' default
"""

import sqlite3
import os

# Path to the SQLite database
DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'habitstreak.db')


def column_exists(cursor, table_name, column_name):
    """
    Check if a column exists in a SQLite table.

    Uses PRAGMA table_info() to get column metadata for a specific table.
    Returns rows with: (cid, name, type, notnull, dflt_value, pk)
    """
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]  # col[1] is the column name
    return column_name in column_names


def run_migration():
    """
    Execute the migration to add the notification_frequency column.

    DETAILED EXPLANATION:

    1. We connect to the SQLite database using sqlite3
    2. We check if 'notification_frequency' already exists in 'habit' table
       - If it exists, we skip (makes this script safe to run multiple times)
       - If it doesn't exist, we proceed with the migration
    3. We execute ALTER TABLE to add the new column:
       - Column name: notification_frequency
       - Data type: VARCHAR(20) (matches SQLAlchemy's db.String(20))
       - Default value: 'daily' - the most common setting
    4. We update any existing rows to ensure they have the default value
    5. We commit the transaction to persist the change
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
        if column_exists(cursor, 'habit', 'notification_frequency'):
            print("SUCCESS: Column 'notification_frequency' already exists in 'habit' table.")
            print("No migration needed - your schema is already up to date!")
            return True

        print("Column 'notification_frequency' not found in 'habit' table.")
        print("Running migration to add the column...")

        # Add the notification_frequency column
        # SQL Breakdown:
        # - ALTER TABLE habit: Modify the 'habit' table structure
        # - ADD COLUMN notification_frequency: Add a new column named 'notification_frequency'
        # - VARCHAR(20): The data type (matches SQLAlchemy db.String(20))
        # - DEFAULT 'daily': New rows and existing rows get this default value
        cursor.execute("""
            ALTER TABLE habit
            ADD COLUMN notification_frequency VARCHAR(20) DEFAULT 'daily'
        """)

        # Update any existing rows that might have NULL (shouldn't happen with DEFAULT, but just in case)
        cursor.execute("""
            UPDATE habit
            SET notification_frequency = 'daily'
            WHERE notification_frequency IS NULL
        """)

        conn.commit()

        # Verify the migration worked
        if column_exists(cursor, 'habit', 'notification_frequency'):
            print("SUCCESS: Migration completed!")
            print("Column 'notification_frequency' has been added to the 'habit' table.")

            # Show the updated table schema
            print("\nUpdated 'habit' table schema:")
            cursor.execute("PRAGMA table_info(habit)")
            columns = cursor.fetchall()
            for col in columns:
                cid, name, col_type, notnull, default, pk = col
                nullable = "NOT NULL" if notnull else "NULL"
                primary = "(PK)" if pk else ""
                default_str = f" DEFAULT {default}" if default else ""
                print(f"  - {name}: {col_type} {nullable}{default_str} {primary}")

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
    print("Adding 'notification_frequency' column to 'habit' table")
    print("=" * 60)
    print()

    success = run_migration()

    print()
    if success:
        print("Migration completed successfully!")
        print("You can now configure notification settings for your habits.")
    else:
        print("Migration failed. Please check the error messages above.")

    print("=" * 60)
