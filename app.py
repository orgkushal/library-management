from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin
from datetime import datetime
import pytz

app = Flask(__name__)
app.config['SECRET_KEY'] = 'orgkushal'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)
login_manager = LoginManager(app)

#User class to manage users table in users database.
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(10), nullable=False)
    requests = db.relationship('Request', backref='user_relationship', lazy=True)

#Book class to manage books table in users database.
class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text)
    genre_id = db.Column(db.Integer, db.ForeignKey('genre.id'), nullable=True)
    requests = db.relationship('Request', backref='books_relationship', lazy=True)
    feedback = db.relationship('Feedback', backref='books_feedback_relationship', lazy=True)
    genre = db.relationship('Genre', backref='books_genres_relationship', lazy=True)

#Genre class to manage all the genres in users database
class Genre(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.Text)
    genre_books = db.relationship('Book', backref='genre_books_relationship', lazy=True)

#Feedback class to manage all the feedbacks by a particular user on a specific book.
class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    feed_book = db.relationship('Book', backref='book_feedback_relationship', lazy=True)

#Request class to manage all the requests of a particular book by a user.
class Request(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    issue_date = db.Column(db.DateTime, default=datetime.utcnow)
    return_date = db.Column(db.DateTime, default=datetime.utcnow) 
    status = db.Column(db.String(20), default='Pending', nullable=False)
    user = db.relationship('User', backref='requests_user_relationship', lazy=True)
    book = db.relationship('Book', backref='requests__books_relationship', lazy=True)



    @staticmethod
    def create_request(user_id, book_id):
        # Check if the book is already allotted to a user
        existing_request = Request.query.filter_by(book_id=book_id, status='Accepted').first()
        if existing_request:
            return None  # Book is already allotted
        
        # Check if there is a pending request for the same book by the same user
        pending_request = Request.query.filter_by(user_id=user_id, book_id=book_id, status='Pending').first()
        if pending_request:
            return pending_request  # User already has a pending request for this book

        # Check the number of currently accepted requests for the user
        accepted_requests_count = Request.query.filter_by(user_id=user_id, status='Accepted').count()

        # Limit the user to issue a maximum of 5 books
        if accepted_requests_count >= 5:
            flash('You have already reached the maximum limit of 5 issued books.', 'warning')
            return None

        # Create a new request
        new_request = Request(user_id=user_id, book_id=book_id, issue_date=datetime.utcnow())
        db.session.add(new_request)
        db.session.commit()
        return new_request

    @app.context_processor
    def utility_processor():
        def convert_to_ist(time):
            # Convert UTC time to IST
            utc_time = time.replace(tzinfo=pytz.UTC)
            ist_time = utc_time.astimezone(pytz.timezone('Asia/Kolkata'))
            return ist_time

        # Return the function to be injected into templates
        return dict(convert_to_ist=convert_to_ist)

@login_manager.user_loader
def load_user(user_id):
    # Return the User object or None if not found
    return User.query.get(int(user_id))

#home page directly loads the login/register page.
@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():

    #incorrect variable is for incorrect username and password check.
    incorrect = False
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        #The admin is redirected to the admin dashboard.
        if username == 'admin' and password == 'admin' and role == 'admin':
            session['role'] = 'admin'
            return redirect(url_for('dashboard_admin'))
        # For regular user login, query the user from the database
        user = User.query.filter_by(username=username, role=role).first()

        if user and user.password == password:
            session['role'] = 'user'
            # Set the user ID in the session upon successful login
            session['user_id'] = user.id

            #The user is redirected to the user Dashboard
            return redirect(url_for('dashboard_user', username=username))

        flash('Login failed. Please check your username, password, and role.', 'danger')
        incorrect = True
    return render_template('login.html', incorrect=incorrect)

#Route to logout of the current user
@app.route('/logout')
def logout():
    # Redirect to the home page or login page
    return redirect(url_for('home'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        role = 'user'  # Set a default role for registration

        if password == confirm_password:
            new_user = User(username=username, password=password, role=role)
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))

        flash('Password and confirm password do not match. Please try again.', 'danger')

    return render_template('register.html')

@app.route('/dashboard_admin', methods=['GET', 'POST'])
def dashboard_admin():
    # Fetch pending requests
    pending_requests = Request.query.filter_by(status='Pending').all()
    
    # Fetch accepted requests along with user information
    accepted_requests = Request.query.filter_by(status='Accepted').all()
    # Fetch all books from the 'books' database
    books = Book.query.all()
    
    return render_template('dashboard_admin.html', username='admin', books=books, 
                           pending_requests=pending_requests, accepted_requests=accepted_requests)

def calculate_days_since_issue(issue_date):
    # Calculate the number of days between the issue date and the current date
    current_date = datetime.utcnow()
    days_since_issue = (current_date - issue_date).days
    return days_since_issue

@app.route('/dashboard_user', methods=['GET', 'POST'])
def dashboard_user():
    # Check if the user is logged in
    if 'user_id' in session:
        user_id = session['user_id']
        user = User.query.filter_by(id=user_id).first()

        # Fetch the user's accepted requests along with the corresponding books
        accepted_requests = Request.query.filter_by(user_id=user_id, status='Accepted').all()
        accepted_books = [(request.book, calculate_days_since_issue(request.issue_date)) for request in accepted_requests]

        return render_template('dashboard_user.html',username = user.username, accepted_books=accepted_books)
    else:
        flash('Please log in to access the user dashboard.', 'danger')
        return render_template('dashboard_user.html')

@app.route('/add_book', methods=['GET', 'POST'])
def add_book():
    genres = Genre.query.all()
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        content = request.form['content']
        genre_id = request.form['genre']

        new_book = Book(title=title, author=author, content=content, genre_id=genre_id)
        db.session.add(new_book)
        db.session.commit()
        flash('Book added successfully!', 'success')

    return render_template('add_new_book.html', genres=genres)

@app.route('/add_genre', methods=['GET', 'POST'])
def add_genre():
    if request.method == 'POST':
        # Retrieve the genre name from the form
        genre_name = request.form['genre_name']
        genre_description = request.form['description']

        # Check if the genre already exists
        existing_genre = Genre.query.filter_by(name=genre_name).first()
        if existing_genre:
            flash('Genre already exists.', 'warning')
        else:
            # Create a new genre
            new_genre = Genre(name=genre_name, description = genre_description)
            db.session.add(new_genre)
            db.session.commit()
            flash('Genre added successfully!', 'success')

        # Redirect to the admin dashboard or any other page
        return redirect(url_for('dashboard_admin'))

    # For GET requests, render the add_genre.html template
    return render_template('add_genre.html')

@app.route('/edit_book/<int:book_id>', methods=['GET', 'POST'])
def edit_book(book_id):
    if request.method == 'POST':
        # Fetch the book from the database using book_id
        book = Book.query.get(book_id)

        if book:
            # Update book details
            book.title = request.form['edit_title']
            book.author = request.form['edit_author']
            book.content = request.form['edit_content']
            selected_genre_id = int(request.form['edit_genre'])
            selected_genre = Genre.query.get(selected_genre_id)
            
            if selected_genre:
                book.genre = selected_genre
            else:
                flash('Selected genre not found.', 'danger')
                return redirect(url_for('display_books', username='admin'))

            db.session.commit()
            flash('Book details updated successfully!', 'success')
        else:
            flash('Book not found.', 'danger')

    return redirect(url_for('display_books', username='admin'))

@app.route('/remove_book/<int:book_id>', methods=['POST'])
def remove_book(book_id):
    book = Book.query.get(book_id)
    if book:
        db.session.delete(book)
        db.session.commit()
        flash('Book removed successfully!', 'success')
    else:
        flash('Book not found.', 'danger')
    return redirect(url_for('display_books'))

@app.route('/display_books', methods=['GET', 'POST'])
def display_books():
    books = Book.query.all()
    genres = Genre.query.all()
    # Fetch accepted requests along with user information
    accepted_requests = Request.query.filter_by(status='Accepted').all()
    return render_template('display_books.html', books=books, genres = genres, accepted_requests=accepted_requests)

@app.route('/request_books', methods=['GET', 'POST'])
def request_books():
    if request.method == 'POST':
        genre_id = request.form.get('genre')

        if genre_id:
            # Fetch all available books in the selected genre
            books = Book.query.filter_by(genre_id=genre_id).all()

            # Filter out books that are already allocated
            allocated_books = set([request.book_id for request in Request.query.filter_by(status='Accepted').all()])

            genre = Genre.query.get(genre_id)
            return render_template('request_books.html', books=books, allocated_books=allocated_books, genre=genre, genres=Genre.query.all())

    # Fetch all available books when the page is first loaded
    books = Book.query.all()
    genres = Genre.query.all()
    allocated_books = set()

    allocated_requests = Request.query.filter_by(status='Accepted').all()
    allocated_books = {request.book_id for request in allocated_requests}
    return render_template('request_books.html', books=books, genres=genres, allocated_books=allocated_books)

@app.route('/request_book/<int:book_id>', methods=['POST'])
def request_book(book_id):
    print("Inside request_book route")
    if request.method == 'POST':
        # Check if the user is logged in
        if 'user_id' in session:
            user_id = session['user_id']
            incorrect = False

            # Check if the user has already reached the maximum limit (5 books)
            accepted_requests_count = Request.query.filter_by(user_id=user_id, status='Accepted').count()
            if accepted_requests_count >= 5:
                incorrect = True
                flash('You have already reached the maximum limit of 5 issued books.', 'warning')
                return render_template('request_books.html', incorrect = incorrect)
            
            # Try to create a new request
            new_request = Request.create_request(user_id, book_id)
            
            if new_request:
                if new_request.status == 'Pending':
                    print("Requesting book")
                    flash('Book requested successfully!', 'success')
                elif new_request.status == 'Accepted':
                    flash('You have already requested this book, and it is accepted.', 'warning')
                elif new_request.status == 'Declined':
                    flash('You have already requested this book, but it is declined. Please try again later.', 'danger')
            else:
                flash('The book is already allotted to another user or you have a pending request for this book.', 'warning')
        else:
            flash('Please log in to request books.', 'danger')

    return redirect(url_for('request_books'))

@app.route('/return_book/<int:request_id>', methods=['POST'])
def return_book(request_id):
    request = Request.query.get(request_id)
    print('Request ::::', request)
    if request:
        # Delete the request from the Request table
        request.return_date = datetime.utcnow()
        print(request.return_date)
        db.session.delete(request)
        db.session.commit()
        flash('Book returned successfully!', 'success')

        # Determine where to redirect based on the user's role in the session
        if 'role' in session and session['role'] == 'admin':
            return redirect(url_for('dashboard_admin'))
        else:
            return redirect(url_for('dashboard_user'))
    else:
        flash('Request not found.', 'danger')
        return redirect(url_for('dashboard_user'))

@app.route('/read_book/<int:book_id>', methods=['GET'])
def read_book(book_id):
    # Fetch the book from the database using book_id
    book = Book.query.get(book_id)

    if book:
        return render_template('read_book.html', book=book)
    else:
        flash('Book not found.', 'danger')
        return redirect(url_for('dashboard_user'))

@app.route('/feedback/<int:book_id>', methods=['GET', 'POST'])
def feedback(book_id):
    if request.method == 'POST':
        feedback_text = request.form.get('feedback')
        rating = request.form.get('rating')

        if 'clear' in request.form:
            # Redirect to the feedback form again with cleared input fields
            return redirect(url_for('feedback', book_id=book_id))

        feedback = Feedback(book_id=book_id, text=feedback_text, rating=rating)
        db.session.add(feedback)
        db.session.commit()

        return redirect(url_for('read_book', book_id=book_id))

    # Render the feedback form template for GET requests
    return render_template('feedback.html', book_id=book_id)

@app.route('/view_feedback/<int:book_id>')
def view_feedback(book_id):
    feedback_for_book = Feedback.query.filter_by(book_id=book_id).all()
    book = Book.query.filter_by(id = book_id).first()

    return render_template('view_feedback.html',book = book, book_id=book_id, feedback=feedback_for_book)

@app.route('/accept_request/<int:request_id>', methods=['POST'])
def accept_request(request_id):
    request = Request.query.get(request_id)
    if request:
        request.status = 'Accepted'
        request.issue_date = datetime.utcnow()
        print(request.issue_date)
        db.session.commit()
        flash('Request accepted successfully!', 'success')
    else:
        flash('Request not found.', 'danger')

    return redirect(url_for('dashboard_admin'))

@app.route('/decline_request/<int:request_id>', methods=['POST'])
def decline_request(request_id):
    request = Request.query.get(request_id)
    if request:
        db.session.delete(request)
        db.session.commit()
        flash('Request declined successfully!', 'success')
    else:
        flash('Request not found.', 'danger')

    return redirect(url_for('dashboard_admin'))

@app.route('/search_books', methods=['GET','POST'])
def search_books():
    term = request.form.get('term', '')
    print('Term:', term)
    # Perform search based on the term (replace this with your actual search logic)
    search_results = Book.query.filter(db.or_(Book.title.ilike(f"%{term}%"), Book.author.ilike(f"%{term}%"))).all()
    accepted_requests = Request.query.filter_by(status='Accepted').all()
    if 'role' in session and session['role'] == 'admin':
            return(render_template('display_books.html', books=search_results, accepted_requests=accepted_requests))
    else:
            return render_template('request_books.html', books=search_results)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port= 8000)
