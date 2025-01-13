from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import random
import string


app = Flask(__name__)
app.secret_key = 'your_secret_key'


def create_connection(db_file):
    connection = None
    try:
        connection = sqlite3.connect(db_file)
    except sqlite3.Error as e:
        print(e)
    return connection


def create_table(connection):
    sql = '''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL CHECK (role IN ('student', 'teacher'))
    )
    '''
    with connection:
        cur = connection.cursor()
        cur.execute(sql)


def create_classes_table(connection):
    sql = '''
    CREATE TABLE IF NOT EXISTS classes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        code TEXT NOT NULL,
        teacher_id INTEGER,
        FOREIGN KEY (teacher_id) REFERENCES users(id)
    )
    '''
    with connection:
        cur = connection.cursor()
        cur.execute(sql)


def create_enrollments_table(connection):
    sql = '''
    CREATE TABLE IF NOT EXISTS enrollments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        class_id INTEGER,
        student_id INTEGER,
        FOREIGN KEY (class_id) REFERENCES classes(id),
        FOREIGN KEY (student_id) REFERENCES users(id)
    )
    '''
    with connection:
        cur = connection.cursor()
        cur.execute(sql)


def create_questions_table(connection):
    sql = '''
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        class_id INTEGER,
        question_text TEXT NOT NULL,
        question_type TEXT NOT NULL CHECK (question_type IN ('open', 'multiple')),
        option_a TEXT,
        option_b TEXT,
        option_c TEXT,
        option_d TEXT,
        correct_option TEXT,
        FOREIGN KEY (class_id) REFERENCES classes(id)
    )
    '''
    with connection:
        cur = connection.cursor()
        cur.execute(sql)


def create_responses_table(connection):
    sql = '''
    CREATE TABLE IF NOT EXISTS responses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_id INTEGER,
        student_id INTEGER,
        class_id INTEGER,
        response_text TEXT NOT NULL,
        FOREIGN KEY (question_id) REFERENCES questions(id),
        FOREIGN KEY (student_id) REFERENCES users(id),
        FOREIGN KEY (class_id) REFERENCES classes(id),
        UNIQUE(question_id, student_id) -- Ensure a student can only respond once to each question
    )
    '''
    with connection:
        cur = connection.cursor()
        cur.execute(sql)


def create_feedback_table(connection):
    sql = '''
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        response_id INTEGER,
        feedback_text TEXT NOT NULL,
        FOREIGN KEY (response_id) REFERENCES responses(id)
    )
    '''
    with connection:
        cur = connection.cursor()
        cur.execute(sql)


def create_chemistry_questions_table(connection):
    sql = '''
    CREATE TABLE IF NOT EXISTS chemistry_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_text TEXT NOT NULL,
        option_a TEXT NOT NULL,
        option_b TEXT NOT NULL,
        option_c TEXT NOT NULL,
        option_d TEXT NOT NULL,
        correct_option TEXT NOT NULL
    )
    '''
    with connection:
        cur = connection.cursor()
        cur.execute(sql)


def create_scores_table(connection):
    sql = '''
    CREATE TABLE IF NOT EXISTS scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        score INTEGER NOT NULL,
        FOREIGN KEY (student_id) REFERENCES users(id)
    )
    '''
    with connection:
        cur = connection.cursor()
        cur.execute(sql)


def insert_user(connection, name, email, password, role):
    sql = ''' INSERT INTO users(name, email, password, role) VALUES(?,?,?,?) '''
    with connection:
        cur = connection.cursor()
        cur.execute(sql, (name, email, password, role))


def check_user_credentials(connection, email, password):
    cur = connection.cursor()
    cur.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
    row = cur.fetchone()
    return row


def drop_table(connection, table_name):
    sql = f"DROP TABLE IF EXISTS {table_name};"
    with connection:
        cur = connection.cursor()
        cur.execute(sql)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email-address']
        password = request.form['password']
        role = request.form['role']
        connection = create_connection('users.db')
        create_table(connection)
        insert_user(connection, name, email, password, role)
        connection.close()
        return redirect(url_for('home'))
    return render_template('registration.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email-address']
        password = request.form['password']
        connection = create_connection('users.db')
        user = check_user_credentials(connection, email, password)
        if user:
            session['email'] = email
            session['user_id'] = user[0]
            session['role'] = user[4]
            connection.close()
            if user[4] == 'teacher':
                return redirect(url_for('teacher_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        else:
            connection.close()
            return render_template('login.html', error='Invalid email or password')
    return render_template('login.html')


@app.route('/')
def home():
    return render_template('login.html')


@app.route('/teacher_dashboard')
def teacher_dashboard():
    if 'role' in session and session['role'] == 'teacher':
        connection = create_connection('users.db')
        cur = connection.cursor()
        cur.execute("SELECT id, name, code FROM classes WHERE teacher_id = (SELECT id FROM users WHERE email = ?)", (session['email'],))
        classes = cur.fetchall()
        connection.close()
        return render_template('teacher_dashboard.html', classes=classes)
    return redirect(url_for('home'))


@app.route('/class_dashboard/<int:class_id>')
def class_dashboard(class_id):
    if 'role' in session and session['role'] == 'teacher':
        connection = create_connection('users.db')
        cur = connection.cursor()
        cur.execute("SELECT name, code FROM classes WHERE id = ?", (class_id,))
        class_info = cur.fetchone()
        cur.execute('''SELECT questions.id, questions.question_text, questions.question_type, questions.option_a, questions.option_b, questions.option_c, questions.option_d
                       FROM questions
                       WHERE questions.class_id = ?''', (class_id,))
        questions = cur.fetchall()
        cur.execute('''SELECT responses.id, users.name, questions.question_text, responses.response_text
                       FROM responses
                       JOIN users ON responses.student_id = users.id
                       JOIN questions ON responses.question_id = questions.id
                       WHERE questions.class_id = ?''', (class_id,))
        responses = cur.fetchall()
        connection.close()
        return render_template('class_dashboard.html', class_name=class_info[0], class_code=class_info[1], questions=questions, responses=responses, class_id=class_id)
    return redirect(url_for('home'))


@app.route('/student_dashboard')
def student_dashboard():
    if 'role' in session and session['role'] == 'student':
        connection = create_connection('users.db')
        cur = connection.cursor()
        cur.execute('''SELECT classes.id, classes.name
                       FROM classes JOIN enrollments ON classes.id = enrollments.class_id
                       WHERE enrollments.student_id = ?''', (session['user_id'],))
        classes = cur.fetchall()


        feedbacks = {}
        for class_id, class_name in classes:
            cur.execute('''SELECT feedback.feedback_text
                           FROM feedback
                           JOIN responses ON feedback.response_id = responses.id
                           WHERE responses.student_id = ? AND responses.class_id = ?''', (session['user_id'], class_id))
            feedbacks[class_id] = cur.fetchall()


        connection.close()
        error = request.args.get('error')
        return render_template('student_dashboard.html', classes=classes, error=error, feedbacks=feedbacks)
    return redirect(url_for('home'))


@app.route('/create_class', methods=['POST'])
def create_class():
    if 'role' in session and session['role'] == 'teacher':
        class_name = request.form['class_name']
        class_code = generate_random_code(6)
        connection = create_connection('users.db')
        cur = connection.cursor()
        cur.execute("SELECT id FROM users WHERE email = ?", (session['email'],))
        teacher_id = cur.fetchone()[0]
        sql = ''' INSERT INTO classes(name, code, teacher_id) VALUES(?,?,?) '''
        with connection:
            cur.execute(sql, (class_name, class_code, teacher_id))
            class_id = cur.lastrowid
        connection.close()
        return redirect(url_for('class_dashboard', class_id=class_id))
    return redirect(url_for('home'))


@app.route('/join_class', methods=['POST'])
def join_class():
    if 'role' in session and session['role'] == 'student':
        class_code = request.form['class_code']
        connection = create_connection('users.db')
        cur = connection.cursor()
        cur.execute("SELECT id FROM classes WHERE code = ?", (class_code,))
        class_id_row = cur.fetchone()
        if class_id_row:
            class_id = class_id_row[0]
            student_id = session['user_id']
            cur.execute("SELECT COUNT(*) FROM enrollments WHERE class_id = ? AND student_id = ?", (class_id, student_id))
            already_enrolled = cur.fetchone()[0] > 0
            if not already_enrolled:
                sql = ''' INSERT INTO enrollments(class_id, student_id) VALUES(?,?) '''
                with connection:
                    cur.execute(sql, (class_id, student_id))
                connection.close()
                return redirect(url_for('student_dashboard'))
            else:
                connection.close()
                return redirect(url_for('student_dashboard', error='You are already enrolled in this class'))
        connection.close()
        return redirect(url_for('student_dashboard', error='Invalid class code'))
    return redirect(url_for('home'))


@app.route('/assign_question/<int:class_id>', methods=['GET', 'POST'])
def assign_question(class_id):
    if 'role' in session and session['role'] == 'teacher':
        if request.method == 'POST':
            question_text = request.form['question_text']
            question_type = request.form['question_type']
            option_a = request.form.get('option_a')
            option_b = request.form.get('option_b')
            option_c = request.form.get('option_c')
            option_d = request.form.get('option_d')
            correct_option = request.form.get('correct_option')
            connection = create_connection('users.db')
            sql = ''' INSERT INTO questions(class_id, question_text, question_type, option_a, option_b, option_c, option_d, correct_option) VALUES(?,?,?,?,?,?,?,?) '''
            with connection:
                cur = connection.cursor()
                cur.execute(sql, (class_id, question_text, question_type, option_a, option_b, option_c, option_d, correct_option))
            connection.close()
            return redirect(url_for('class_dashboard', class_id=class_id))
        return render_template('assign.html', class_id=class_id)
    return redirect(url_for('home'))


@app.route('/student_class_dashboard/<int:class_id>')
def student_class_dashboard(class_id):
    if 'role' in session and session['role'] == 'student':
        connection = create_connection('users.db')
        cur = connection.cursor()
        cur.execute("SELECT name, code FROM classes WHERE id = ?", (class_id,))
        class_info = cur.fetchone()
        cur.execute('''SELECT questions.id, questions.question_text, questions.question_type, questions.option_a, questions.option_b, questions.option_c, questions.option_d
                       FROM questions
                       WHERE questions.class_id = ?''', (class_id,))
        questions = cur.fetchall()
        cur.execute('''SELECT responses.question_id FROM responses WHERE responses.student_id = ?''', (session['user_id'],))
        answered_questions = [row[0] for row in cur.fetchall()]
        connection.close()
        return render_template('student_class_dashboard.html', class_info=class_info, questions=questions, answered_questions=answered_questions, class_id=class_id)
    return redirect(url_for('home'))


@app.route('/submit_response/<int:class_id>/<int:question_id>', methods=['GET', 'POST'])
def submit_response(class_id, question_id):
    if 'role' in session and session['role'] == 'student':
        if request.method == 'POST':
            response_text = request.form['response_text']
            connection = create_connection('users.db')
            cur = connection.cursor()
            cur.execute("SELECT id FROM users WHERE email = ?", (session['email'],))
            student_id = cur.fetchone()[0]
            sql = ''' INSERT INTO responses(question_id, student_id, class_id, response_text) VALUES(?,?,?,?) '''
            with connection:
                cur.execute(sql, (question_id, student_id, class_id, response_text))
            connection.close()
            return redirect(url_for('student_class_dashboard', class_id=class_id))
        return render_template('submit.html', class_id=class_id, question_id=question_id)
    return redirect(url_for('home'))


@app.route('/view_submissions/<int:class_id>')
def view_submissions(class_id):
    if 'role' in session and session['role'] == 'teacher':
        connection = create_connection('users.db')
        cur = connection.cursor()
        cur.execute('''SELECT responses.id, users.name, questions.question_text, responses.response_text
                       FROM responses
                       JOIN users ON responses.student_id = users.id
                       JOIN questions ON responses.question_id = questions.id
                       WHERE questions.class_id = ?''', (class_id,))
        responses = cur.fetchall()
        connection.close()
        return render_template('view_submissions.html', responses=responses, class_id=class_id)
    return redirect(url_for('home'))


@app.route('/provide_feedback/<int:response_id>', methods=['POST'])
def provide_feedback(response_id):
    if 'role' in session and session['role'] == 'teacher':
        feedback_text = request.form['feedback_text']
        class_id = request.form['class_id']
        connection = create_connection('users.db')
        sql = ''' INSERT INTO feedback(response_id, feedback_text) VALUES(?,?) '''
        with connection:
            cur = connection.cursor()
            cur.execute(sql, (response_id, feedback_text))
        connection.close()
        return redirect(url_for('view_submissions', class_id=class_id))
    return redirect(url_for('home'))


def generate_random_code(length):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


chemistry_questions = [
    {
        "id": 1,
        "question_text": "What is the atomic number of Hydrogen?",
        "option_a": "1",
        "option_b": "2",
        "option_c": "3",
        "option_d": "4",
        "correct_option": "a"
    },
    {
        "id": 2,
        "question_text": "What is the chemical symbol for Helium?",
        "option_a": "H",
        "option_b": "He",
        "option_c": "Hi",
        "option_d": "Ho",
        "correct_option": "b"
    },
    {
        "id": 3,
        "question_text": "How many electrons does Carbon have?",
        "option_a": "4",
        "option_b": "5",
        "option_c": "6",
        "option_d": "7",
        "correct_option": "c"
    },
    {
        "id": 4,
        "question_text": "What is the molecular formula of Water?",
        "option_a": "H2O",
        "option_b": "O2",
        "option_c": "H2O2",
        "option_d": "OH",
        "correct_option": "a"
    },
    {
        "id": 5,
        "question_text": "What is the pH level of pure water?",
        "option_a": "5",
        "option_b": "6",
        "option_c": "7",
        "option_d": "8",
        "correct_option": "c"
    },
    {
        "id": 6,
        "question_text": "What is the chemical formula for table salt?",
        "option_a": "NaCl",
        "option_b": "KCl",
        "option_c": "Na2SO4",
        "option_d": "NaOH",
        "correct_option": "a"
    },
    {
        "id": 7,
        "question_text": "What element is represented by the symbol 'O'?",
        "option_a": "Oxygen",
        "option_b": "Osmium",
        "option_c": "Oganesson",
        "option_d": "Oxygenium",
        "correct_option": "a"
    },
    {
        "id": 8,
        "question_text": "What is the atomic number of Neon?",
        "option_a": "8",
        "option_b": "9",
        "option_c": "10",
        "option_d": "11",
        "correct_option": "c"
    },
    {
        "id": 9,
        "question_text": "Which element has the highest atomic number?",
        "option_a": "Oxygen",
        "option_b": "Uranium",
        "option_c": "Carbon",
        "option_d": "Hydrogen",
        "correct_option": "b"
    },
    {
        "id": 10,
        "question_text": "What is the chemical formula for ammonia?",
        "option_a": "NH3",
        "option_b": "NO2",
        "option_c": "NH4",
        "option_d": "N2O",
        "correct_option": "a"
    },
    {
        "id": 11,
        "question_text": "What is the most abundant gas in Earth's atmosphere?",
        "option_a": "Oxygen",
        "option_b": "Nitrogen",
        "option_c": "Carbon Dioxide",
        "option_d": "Hydrogen",
        "correct_option": "b"
    },
    {
        "id": 12,
        "question_text": "What is the chemical symbol for gold?",
        "option_a": "Ag",
        "option_b": "Au",
        "option_c": "Pb",
        "option_d": "Gd",
        "correct_option": "b"
    },
    {
        "id": 13,
        "question_text": "What element is diamond made of?",
        "option_a": "Carbon",
        "option_b": "Silicon",
        "option_c": "Oxygen",
        "option_d": "Sulfur",
        "correct_option": "a"
    },
    {
        "id": 14,
        "question_text": "What is the chemical formula for methane?",
        "option_a": "CH3",
        "option_b": "CH4",
        "option_c": "C2H4",
        "option_d": "C2H6",
        "correct_option": "b"
    },
    {
        "id": 15,
        "question_text": "Which of these elements is a noble gas?",
        "option_a": "Oxygen",
        "option_b": "Nitrogen",
        "option_c": "Chlorine",
        "option_d": "Argon",
        "correct_option": "d"
    },
    {
        "id": 16,
        "question_text": "What is the chemical formula for baking soda?",
        "option_a": "NaCl",
        "option_b": "NaHCO3",
        "option_c": "Na2CO3",
        "option_d": "NaOH",
        "correct_option": "b"
    },
    {
        "id": 17,
        "question_text": "What is the atomic number of Iron?",
        "option_a": "24",
        "option_b": "26",
        "option_c": "28",
        "option_d": "30",
        "correct_option": "b"
    },
    {
        "id": 18,
        "question_text": "What is the main gas found in the air we breathe?",
        "option_a": "Oxygen",
        "option_b": "Hydrogen",
        "option_c": "Nitrogen",
        "option_d": "Carbon Dioxide",
        "correct_option": "c"
    },
    {
        "id": 19,
        "question_text": "What element has the chemical symbol 'Fe'?",
        "option_a": "Fluorine",
        "option_b": "Iron",
        "option_c": "Francium",
        "option_d": "Fermium",
        "correct_option": "b"
    },
    {
        "id": 20,
        "question_text": "What is the pH value of a neutral substance?",
        "option_a": "1",
        "option_b": "7",
        "option_c": "14",
        "option_d": "0",
        "correct_option": "b"
    },
    {
        "id": 21,
        "question_text": "Which element is known as the 'King of Chemicals'?",
        "option_a": "Sulfur",
        "option_b": "Carbon",
        "option_c": "Nitrogen",
        "option_d": "Hydrogen",
        "correct_option": "a"
    },
    {
        "id": 22,
        "question_text": "What is the atomic number of Lead?",
        "option_a": "82",
        "option_b": "83",
        "option_c": "84",
        "option_d": "85",
        "correct_option": "a"
    },
    {
        "id": 23,
        "question_text": "What is the chemical formula for rust?",
        "option_a": "Fe2O3",
        "option_b": "FeO",
        "option_c": "Fe3O4",
        "option_d": "Fe2O",
        "correct_option": "a"
    },
    {
        "id": 24,
        "question_text": "What is the chemical symbol for silver?",
        "option_a": "Si",
        "option_b": "Ag",
        "option_c": "Au",
        "option_d": "Pb",
        "correct_option": "b"
    },
    {
        "id": 25,
        "question_text": "What element is used in pencils?",
        "option_a": "Lead",
        "option_b": "Carbon",
        "option_c": "Graphite",
        "option_d": "Silicon",
        "correct_option": "c"
    },
    {
        "id": 26,
        "question_text": "What is the chemical formula for hydrochloric acid?",
        "option_a": "HCl",
        "option_b": "H2SO4",
        "option_c": "HNO3",
        "option_d": "H2CO3",
        "correct_option": "a"
    },
    {
        "id": 27,
        "question_text": "What is the chemical name for table sugar?",
        "option_a": "Fructose",
        "option_b": "Glucose",
        "option_c": "Sucrose",
        "option_d": "Lactose",
        "correct_option": "c"
    },
    {
        "id": 28,
        "question_text": "What is the chemical symbol for potassium?",
        "option_a": "K",
        "option_b": "P",
        "option_c": "Pt",
        "option_d": "Po",
        "correct_option": "a"
    },
    {
        "id": 29,
        "question_text": "What is the chemical formula for sulfuric acid?",
        "option_a": "H2SO3",
        "option_b": "H2SO4",
        "option_c": "H2S",
        "option_d": "HSO4",
        "correct_option": "b"
    },
    {
        "id": 30,
        "question_text": "What is the atomic number of Zinc?",
        "option_a": "28",
        "option_b": "29",
        "option_c": "30",
        "option_d": "31",
        "correct_option": "c"
    }
]


@app.route('/puzzle', methods=['GET', 'POST'])
def puzzle():
    if request.method == 'POST':
        # Handle form submission
        selected_answers = request.form.to_dict()
        return redirect(url_for('puzzle'))
    else:
        # Select a random question
        question = random.choice(chemistry_questions)
        return render_template('puzzle.html', questions=[question])


if __name__ == '__main__':
    connection = create_connection('users.db')
    drop_table(connection, 'responses')
    drop_table(connection, 'questions')
    create_table(connection)
    create_classes_table(connection)
    create_enrollments_table(connection)
    create_questions_table(connection)
    create_responses_table(connection)
    create_feedback_table(connection)
    create_chemistry_questions_table(connection)
    create_scores_table(connection)
    connection.close()
    app.run(debug=True)