"""
Migration script to add ISUS (I Stand Up Sitting) charity to the database.
Run this if you already have an existing database with anti-charities.
"""

from app import app, db, AntiCharity

def migrate():
    with app.app_context():
        # Check if ISUS already exists
        existing = AntiCharity.query.filter_by(name="ISUS - I Stand Up Sitting").first()

        if existing:
            print("ISUS already exists in the database!")
            return

        # Add ISUS
        isus = AntiCharity(
            name="ISUS - I Stand Up Sitting",
            category="lifestyle",
            description="Promoting the radical art of standing up while remaining completely sedentary. Because why walk when you can just... not?"
        )

        db.session.add(isus)
        db.session.commit()

        print("Successfully added ISUS to the database!")
        print(f"ID: {isus.id}")
        print(f"Name: {isus.name}")
        print(f"Category: {isus.category}")
        print(f"Description: {isus.description}")


if __name__ == '__main__':
    migrate()
