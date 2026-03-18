"""
Habit Streak Insurance - POC
A habit tracking app that uses loss aversion: miss a day, and your money goes to a cause you despise.
"""

from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps
import os

app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-prod')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///habitstreak.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app, supports_credentials=True)
db = SQLAlchemy(app)

# =============================================================================
# DATABASE MODELS
# =============================================================================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Subscription info (mocked for POC)
    subscription_tier = db.Column(db.String(20), default='free')  # free, basic ($4.99), pro ($9.99)

    habits = db.relationship('Habit', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'subscription_tier': self.subscription_tier,
            'created_at': self.created_at.isoformat()
        }


class HabitCategory(db.Model):
    """Pre-defined categories for habits"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    icon = db.Column(db.String(10))  # Emoji icon for the category
    color = db.Column(db.String(20))  # CSS color for styling
    description = db.Column(db.String(255))

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'icon': self.icon,
            'color': self.color,
            'description': self.description
        }


class AntiCharity(db.Model):
    """Pre-defined organizations users can select as their 'anti-charity'"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # political, environmental, social, etc.
    description = db.Column(db.String(255))

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'description': self.description
        }


class Habit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # Category
    category_id = db.Column(db.Integer, db.ForeignKey('habit_category.id'))

    # Stake configuration
    weekly_stake = db.Column(db.Float, default=5.00)  # Amount at risk per week
    anti_charity_id = db.Column(db.Integer, db.ForeignKey('anti_charity.id'))

    # Streak tracking
    current_streak = db.Column(db.Integer, default=0)
    longest_streak = db.Column(db.Integer, default=0)

    # Notification settings
    notification_frequency = db.Column(db.String(20), default='daily')  # multiple_daily, daily, weekly, off

    category = db.relationship('HabitCategory')
    anti_charity = db.relationship('AntiCharity')
    check_ins = db.relationship('CheckIn', backref='habit', lazy=True, cascade='all, delete-orphan')
    donations = db.relationship('Donation', backref='habit', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category.to_dict() if self.category else None,
            'weekly_stake': self.weekly_stake,
            'anti_charity': self.anti_charity.to_dict() if self.anti_charity else None,
            'current_streak': self.current_streak,
            'longest_streak': self.longest_streak,
            'notification_frequency': self.notification_frequency,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'checked_in_today': self.checked_in_today()
        }

    def checked_in_today(self):
        today = datetime.utcnow().date()
        return any(c.date.date() == today for c in self.check_ins)


class CheckIn(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    habit_id = db.Column(db.Integer, db.ForeignKey('habit.id'), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'habit_id': self.habit_id,
            'date': self.date.isoformat()
        }


class Donation(db.Model):
    """Tracks (mock) donations triggered by missed days"""
    id = db.Column(db.Integer, primary_key=True)
    habit_id = db.Column(db.Integer, db.ForeignKey('habit.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    anti_charity_id = db.Column(db.Integer, db.ForeignKey('anti_charity.id'))
    triggered_at = db.Column(db.DateTime, default=datetime.utcnow)
    missed_date = db.Column(db.Date, nullable=False)

    # For POC, this is always 'simulated'
    status = db.Column(db.String(20), default='simulated')  # simulated, pending, completed

    anti_charity = db.relationship('AntiCharity')

    def to_dict(self):
        return {
            'id': self.id,
            'habit_id': self.habit_id,
            'amount': self.amount,
            'anti_charity': self.anti_charity.to_dict() if self.anti_charity else None,
            'missed_date': self.missed_date.isoformat(),
            'triggered_at': self.triggered_at.isoformat(),
            'status': self.status
        }


# =============================================================================
# AUTH HELPERS
# =============================================================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


def get_current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None


# =============================================================================
# API ROUTES - AUTH
# =============================================================================

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()

    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password required'}), 400

    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 409

    user = User(email=data['email'])
    user.set_password(data['password'])
    db.session.add(user)
    db.session.commit()

    session['user_id'] = user.id
    return jsonify({'user': user.to_dict()}), 201


@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()

    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password required'}), 400

    user = User.query.filter_by(email=data['email']).first()

    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401

    session['user_id'] = user.id
    return jsonify({'user': user.to_dict()})


@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({'message': 'Logged out'})


@app.route('/api/auth/me', methods=['GET'])
@login_required
def get_me():
    user = get_current_user()
    return jsonify({'user': user.to_dict()})


# =============================================================================
# API ROUTES - HABIT CATEGORIES
# =============================================================================

@app.route('/api/habit-categories', methods=['GET'])
@login_required
def get_habit_categories():
    categories = HabitCategory.query.all()
    return jsonify({'categories': [c.to_dict() for c in categories]})


# =============================================================================
# API ROUTES - ANTI-CHARITIES
# =============================================================================

@app.route('/api/anti-charities', methods=['GET'])
@login_required
def get_anti_charities():
    charities = AntiCharity.query.all()
    return jsonify({'anti_charities': [c.to_dict() for c in charities]})


# =============================================================================
# API ROUTES - HABITS
# =============================================================================

@app.route('/api/habits', methods=['GET'])
@login_required
def get_habits():
    user = get_current_user()
    habits = Habit.query.filter_by(user_id=user.id, is_active=True).all()
    return jsonify({'habits': [h.to_dict() for h in habits]})


@app.route('/api/habits', methods=['POST'])
@login_required
def create_habit():
    user = get_current_user()
    data = request.get_json()

    if not data or not data.get('name'):
        return jsonify({'error': 'Habit name required'}), 400

    habit = Habit(
        user_id=user.id,
        name=data['name'],
        description=data.get('description', ''),
        category_id=data.get('category_id'),
        weekly_stake=data.get('weekly_stake', 5.00),
        anti_charity_id=data.get('anti_charity_id'),
        notification_frequency=data.get('notification_frequency', 'daily')
    )

    db.session.add(habit)
    db.session.commit()

    return jsonify({'habit': habit.to_dict()}), 201


@app.route('/api/habits/<int:habit_id>', methods=['PUT'])
@login_required
def update_habit(habit_id):
    user = get_current_user()
    habit = Habit.query.filter_by(id=habit_id, user_id=user.id).first()

    if not habit:
        return jsonify({'error': 'Habit not found'}), 404

    data = request.get_json()

    if 'name' in data:
        habit.name = data['name']
    if 'description' in data:
        habit.description = data['description']
    if 'category_id' in data:
        habit.category_id = data['category_id']
    if 'weekly_stake' in data:
        habit.weekly_stake = data['weekly_stake']
    if 'anti_charity_id' in data:
        habit.anti_charity_id = data['anti_charity_id']
    if 'is_active' in data:
        habit.is_active = data['is_active']
    if 'notification_frequency' in data:
        habit.notification_frequency = data['notification_frequency']

    db.session.commit()
    return jsonify({'habit': habit.to_dict()})


@app.route('/api/habits/<int:habit_id>', methods=['DELETE'])
@login_required
def delete_habit(habit_id):
    user = get_current_user()
    habit = Habit.query.filter_by(id=habit_id, user_id=user.id).first()

    if not habit:
        return jsonify({'error': 'Habit not found'}), 404

    db.session.delete(habit)
    db.session.commit()
    return jsonify({'message': 'Habit deleted'})


# =============================================================================
# API ROUTES - CHECK-INS
# =============================================================================

@app.route('/api/habits/<int:habit_id>/checkin', methods=['POST'])
@login_required
def check_in(habit_id):
    user = get_current_user()
    habit = Habit.query.filter_by(id=habit_id, user_id=user.id).first()

    if not habit:
        return jsonify({'error': 'Habit not found'}), 404

    # Check if already checked in today
    if habit.checked_in_today():
        return jsonify({'error': 'Already checked in today', 'habit': habit.to_dict()}), 400

    # Create check-in
    check_in = CheckIn(habit_id=habit.id)
    db.session.add(check_in)

    # Update streak
    habit.current_streak += 1
    if habit.current_streak > habit.longest_streak:
        habit.longest_streak = habit.current_streak

    db.session.commit()

    return jsonify({
        'message': 'Checked in successfully!',
        'habit': habit.to_dict(),
        'streak': habit.current_streak
    })


@app.route('/api/habits/<int:habit_id>/history', methods=['GET'])
@login_required
def get_habit_history(habit_id):
    user = get_current_user()
    habit = Habit.query.filter_by(id=habit_id, user_id=user.id).first()

    if not habit:
        return jsonify({'error': 'Habit not found'}), 404

    check_ins = CheckIn.query.filter_by(habit_id=habit.id).order_by(CheckIn.date.desc()).limit(30).all()
    donations = Donation.query.filter_by(habit_id=habit.id).order_by(Donation.triggered_at.desc()).limit(30).all()

    return jsonify({
        'habit': habit.to_dict(),
        'check_ins': [c.to_dict() for c in check_ins],
        'donations': [d.to_dict() for d in donations]
    })


# =============================================================================
# API ROUTES - DONATIONS / MISSED DAYS
# =============================================================================

@app.route('/api/donations', methods=['GET'])
@login_required
def get_donations():
    user = get_current_user()
    habit_ids = [h.id for h in user.habits]
    donations = Donation.query.filter(Donation.habit_id.in_(habit_ids)).order_by(Donation.triggered_at.desc()).all()

    total_donated = sum(d.amount for d in donations)

    return jsonify({
        'donations': [d.to_dict() for d in donations],
        'total_donated': total_donated
    })


@app.route('/api/simulate-missed-day', methods=['POST'])
@login_required
def simulate_missed_day():
    """
    POC endpoint to simulate a missed day and trigger a donation.
    In production, this would be handled by a scheduled job.
    """
    user = get_current_user()
    data = request.get_json()
    habit_id = data.get('habit_id')

    if not habit_id:
        return jsonify({'error': 'habit_id required'}), 400

    habit = Habit.query.filter_by(id=habit_id, user_id=user.id).first()

    if not habit:
        return jsonify({'error': 'Habit not found'}), 404

    if not habit.anti_charity_id:
        return jsonify({'error': 'No anti-charity set for this habit'}), 400

    # Calculate daily stake (weekly / 7)
    daily_stake = habit.weekly_stake / 7

    # Create mock donation
    donation = Donation(
        habit_id=habit.id,
        amount=round(daily_stake, 2),
        anti_charity_id=habit.anti_charity_id,
        missed_date=datetime.utcnow().date() - timedelta(days=1),
        status='simulated'
    )

    # Reset streak
    habit.current_streak = 0

    db.session.add(donation)
    db.session.commit()

    return jsonify({
        'message': f'OUCH! ${donation.amount:.2f} donated to {habit.anti_charity.name}',
        'donation': donation.to_dict(),
        'habit': habit.to_dict()
    })


# =============================================================================
# API ROUTES - DASHBOARD STATS
# =============================================================================

@app.route('/api/dashboard', methods=['GET'])
@login_required
def get_dashboard():
    user = get_current_user()
    habits = Habit.query.filter_by(user_id=user.id, is_active=True).all()

    habit_ids = [h.id for h in habits]
    donations = Donation.query.filter(Donation.habit_id.in_(habit_ids)).all()

    total_donated = sum(d.amount for d in donations)
    total_check_ins = sum(len(h.check_ins) for h in habits)
    best_streak = max((h.longest_streak for h in habits), default=0)

    # Calculate money at risk this week
    money_at_risk = sum(h.weekly_stake for h in habits if not h.checked_in_today())

    return jsonify({
        'stats': {
            'total_habits': len(habits),
            'total_check_ins': total_check_ins,
            'total_donated': total_donated,
            'best_streak': best_streak,
            'money_at_risk_today': round(money_at_risk / 7, 2)
        },
        'habits': [h.to_dict() for h in habits]
    })


# =============================================================================
# STATIC FILES
# =============================================================================

@app.route('/')
def serve_landing():
    return send_from_directory('static', 'landing.html')


@app.route('/app')
def serve_app():
    return send_from_directory('static', 'index.html')


@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)


# =============================================================================
# DATABASE INITIALIZATION
# =============================================================================

def init_db():
    """Initialize database and seed with categories and anti-charities"""
    with app.app_context():
        db.create_all()

        # Seed habit categories if empty
        if HabitCategory.query.count() == 0:
            habit_categories = [
                HabitCategory(name="Health & Fitness", icon="💪", color="#43a047",
                             description="Exercise, diet, sleep, and physical wellness"),
                HabitCategory(name="Productivity", icon="📈", color="#1e88e5",
                             description="Work tasks, focus time, and getting things done"),
                HabitCategory(name="Mindfulness", icon="🧘", color="#8e24aa",
                             description="Meditation, journaling, and mental wellness"),
                HabitCategory(name="Finance", icon="💰", color="#f9a825",
                             description="Saving, budgeting, and financial goals"),
                HabitCategory(name="Learning", icon="📚", color="#00acc1",
                             description="Study, reading, and skill development"),
                HabitCategory(name="Social", icon="👥", color="#e91e63",
                             description="Relationships, networking, and connection"),
                HabitCategory(name="Self-Care", icon="✨", color="#ff7043",
                             description="Personal care, hygiene, and wellness routines"),
                HabitCategory(name="Creative", icon="🎨", color="#ab47bc",
                             description="Art, writing, music, and creative pursuits"),
            ]

            for hc in habit_categories:
                db.session.add(hc)

            db.session.commit()
            print("Database initialized with habit categories!")

        # Seed anti-charities if empty
        if AntiCharity.query.count() == 0:
            anti_charities = [
                # Political - Left
                AntiCharity(name="Republican National Committee", category="political",
                           description="The primary political committee of the Republican Party"),
                AntiCharity(name="NRA Foundation", category="political",
                           description="National Rifle Association's charitable arm"),
                AntiCharity(name="Heritage Foundation", category="political",
                           description="Conservative think tank"),

                # Political - Right
                AntiCharity(name="Democratic National Committee", category="political",
                           description="The primary political committee of the Democratic Party"),
                AntiCharity(name="ACLU Foundation", category="political",
                           description="American Civil Liberties Union"),
                AntiCharity(name="Planned Parenthood", category="political",
                           description="Reproductive health organization"),

                # Environmental
                AntiCharity(name="American Petroleum Institute", category="environmental",
                           description="Oil and gas industry trade association"),
                AntiCharity(name="Greenpeace", category="environmental",
                           description="Environmental activism organization"),

                # Sports Rivals (lighter options)
                AntiCharity(name="Yankees Foundation", category="sports",
                           description="New York Yankees charitable foundation"),
                AntiCharity(name="Cowboys Foundation", category="sports",
                           description="Dallas Cowboys charitable foundation"),
                AntiCharity(name="Lakers Youth Foundation", category="sports",
                           description="Los Angeles Lakers charitable foundation"),

                # Tech
                AntiCharity(name="Meta Open Source Fund", category="tech",
                           description="Meta's open source initiatives"),

                # Lifestyle (satirical)
                AntiCharity(name="ISUS - I Stand Up Sitting", category="lifestyle",
                           description="Promoting the radical art of standing up while remaining completely sedentary. Because why walk when you can just... not?"),
            ]

            for ac in anti_charities:
                db.session.add(ac)

            db.session.commit()
            print("Database initialized with anti-charities!")


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
