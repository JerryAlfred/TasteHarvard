import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from helpers import apology, apology_student, apology_visitor, login_required, success_student, success_visitor, success

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached


@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# We store our database in SQLite "taste"
db = SQL("sqlite:///taste.db")

# Register the new user to our db and log them in


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "GET":
        return render_template("register.html")

    else:

        # Collect the info the "POST" html
        username = request.form.get("username")
        name = request.form.get("name")
        surname = request.form.get("surname")

        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        email = request.form.get("email")

        # Respectively check whether username/password/password_2/surname/name is blank, or if 2 passwords don't match
        if not username:
            return apology("Missing username!")
        elif not password:
            return apology("Missing password!")
        elif not name:
            return apology("Missing name!")
        elif not surname:
            return apology("Missing surname!")
        elif not confirmation:
            return apology("Missing confirmation!")
        elif not email:
            return apology("Missing email address!")
        elif password != confirmation:
            return apology("Passwords must match!")
        password_hash = generate_password_hash(password)
        person = request.form.get("person")

        # If the user chooses to log in as a student, the data will be recorded into the "student" table
        if person == "student":
            result = db.execute("INSERT INTO student (username, hash, email, Lname, Fname) VALUES(:username, :hash, :email, :surname, :name)",
                                username=username, hash=password_hash, email=email, surname=surname, name=name)
            if not result:
                return apology("Looks like that account already exists!")
            session["user_id"] = result
            return redirect("/student/index")

        # If the user selects "visitor", their information becomes recorded in the "visitor" table
        else:
            result = db.execute("INSERT INTO visitor (username, hash, email, Lname, Fname) VALUES(:username, :hash, :email, :surname, :name)",
                                username=username, hash=password_hash, email=email, surname=surname, name=name)
            if not result:
                return apology("Looks like that account already exists!")
            # set up the session to keep user logged in
            session["user_id"] = result
            return redirect("/visitor/index")


# From the course's TF
@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        person = request.form.get("person")

        if person == "student":

            # Query database for username
            rows = db.execute("SELECT * FROM student WHERE username = :username",
                              username=request.form.get("username"))
        else:
            rows = db.execute("SELECT * FROM visitor WHERE username = :username",
                              username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        if person == "student":
            # Remember which student user has logged in
            session["user_id"] = rows[0]["student_id"]
            return redirect("/student")

        else:
            session["user_id"] = rows[0]["visitor_id"]
            return redirect("/visitor")

    # If user is trying to access the page, we will present this html
    else:
        return render_template("login.html")


@app.route("/student/logout")
def logout_student():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/student")


@app.route("/visitor/logout")
def logout_visitor():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/visitor")


# Directs to the welcome page
@app.route("/")
def index():
    return render_template("index.html")


# Main welcome page for any user
@app.route("/index")
def index_index():
    return render_template("index.html")


# Redirects to student mainpage after student login
@app.route("/student")
@login_required
def home_student():
    return render_template("student.html")


@app.route("/visitor")
@login_required
def home_visitor():
    return render_template("visitor.html")


# Function, since the trans_history will be written in the way of "1---FRI---Jerry", so to get rid of the first "1---" I am creating this function
def cut(trans_history):
    for trans in trans_history:
        trans["day"] = trans["day"][2:5]
    return trans_history


# The next 4 functions are similar in the sense that they all retrieve data from the database, and present them in our HTML (through jinja). These functions all send out the list to the HTML.
@app.route("/student/history", methods=["GET"])
@login_required
def history_student():
    student_id = session["user_id"]
    trans_history = db.execute("SELECT schedule.visitor_id, day, slot, Fname, Lname FROM schedule, visitor WHERE visitor.visitor_id = schedule.visitor_id AND student_id = :student_id AND confirmation_status = :confirmation_status ORDER BY day, slot",
                               student_id=student_id, confirmation_status="Booked")
    return render_template("student/history.html", trans_history=cut(trans_history))


# The difference between student index and history, is history has all the "booking" records, and index has both "bookign" and the timeslots that are selected free by student by hasn't been booked by any visitor
@app.route("/student/index", methods=["GET"])
@login_required
def index_student():
    student_id = session["user_id"]
    trans_history = db.execute("SELECT schedule.visitor_id, day, slot, confirmation_status, Fname, Lname FROM schedule, visitor WHERE visitor.visitor_id = schedule.visitor_id AND student_id = :student_id AND confirmation_status IN ('Booked', 'Selected') ORDER BY day, slot",
                               student_id=student_id)
    return render_template("student/index.html", trans_history=cut(trans_history))


# Here history and index for visitor does the same job, showing the booking records of visitor with each student
# The reason why there are 2 identical one is for UI design, where user can see the info both in their homepage and in clicking history
@app.route("/visitor/history", methods=["GET"])
@login_required
def history_visitor():
    visitor_id = session["user_id"]
    trans_history = db.execute("SELECT schedule.student_id, day, slot, Fname FROM schedule, student WHERE student.student_id = schedule.student_id AND visitor_id = :visitor_id AND confirmation_status = :confirmation_status ORDER BY day, slot",
                               visitor_id=visitor_id, confirmation_status="Booked")
    return render_template("visitor/history.html", trans_history=cut(trans_history))


@app.route("/visitor/index", methods=["GET"])
@login_required
def index_visitor():
    visitor_id = session["user_id"]
    trans_history = db.execute("SELECT schedule.student_id, day, slot, Fname FROM schedule, student WHERE student.student_id = schedule.student_id AND visitor_id = :visitor_id AND confirmation_status = :confirmation_status ORDER BY day, slot",
                               visitor_id=visitor_id, confirmation_status="Booked")
    return render_template("visitor/history.html", trans_history=cut(trans_history))


# Function where the student can select a time slot for the week
@app.route("/student/select-time-slot", methods=["GET", "POST"])
@login_required
def select_student():

    if request.method == "GET":
        return render_template("student/select-time-slot.html")
    else:

        # Take the data submitted by the user
        student_id = session["user_id"]
        student_name = db.execute("SELECT Fname FROM student WHERE student_id = :student_id", student_id=student_id)
        student_day = request.form.get("student_day")
        student_slot = request.form.get("student_slot")

        if not student_day:
            return apology_student("You forgot to select a day!")
        if not student_slot:
            return apology_student("You forgot to choose a time!")

        # Selects the time slots which have status "Slot_cancelled"
        times = db.execute("SELECT student_id, day, slot, confirmation_status FROM schedule WHERE confirmation_status = :confirmation_status",
                           confirmation_status="Slot_cancelled")
        if times:

            # Iterates over the list "times"
            for i in range(len(times)):

                # Checks if this specific time slot for this student is in a dictionary in "times"
                if times[i].get('student_id') == student_id and times[i].get('day') == student_day and times[i].get('slot') == student_slot:
                    rows = db.execute("UPDATE schedule SET confirmation_status = :confirmation_status",
                                      confirmation_status="Selected")
                    student_day = request.form.get("student_day")[2:]
                    return success_student(f"You have successfully re-selected your time on {student_day} at {student_slot}")

        # Selects the time slots which have status "App_cancelled_stu"
        app_canceled = db.execute("SELECT student_id, day, slot, confirmation_status FROM schedule WHERE confirmation_status = :confirmation_status",
                                  confirmation_status="App_cancelled_stu")
        if app_canceled:

            # Iterates over the list "app_canceled"
            for i in range(len(app_canceled)):

                # Checks if this specific time slot for this student is in a dictionary in "app_canceled"
                if app_canceled[i].get('student_id') == student_id and app_canceled[i].get('day') == student_day and app_canceled[i].get('slot') == student_slot:
                    rows = db.execute("UPDATE schedule SET confirmation_status = :confirmation_status",
                                      confirmation_status="Selected")
                    student_day = request.form.get("student_day")[2:]
                    return success_student(f"You have re-selected your time on {student_day} at {student_slot}")

        # Selects the time slots which have status "App_cancelled_vis"
        vis_canceled = db.execute("SELECT student_id, day, slot, confirmation_status FROM schedule WHERE confirmation_status = :confirmation_status",
                                  confirmation_status="App_cancelled_vis")
        if vis_canceled:

            # Iterates over the list "vis_canceled"
            for i in range(len(vis_canceled)):

                # Checks if this specific time slot for this student is in a dictionary in "vis_canceled"
                if vis_canceled[i].get('student_id') == student_id and vis_canceled[i].get('day') == student_day and vis_canceled[i].get('slot') == student_slot:
                    rows = db.execute("UPDATE schedule SET confirmation_status = :confirmation_status",
                                      confirmation_status="Selected")
                    student_day = request.form.get("student_day")[2:]
                    return success_student(f"You have successfully selected your time on {student_day} at {student_slot}")

        # Checks if this specific time slot already exists in "schedule" with the confirmation_status "Booked"
        booked = db.execute("SELECT student_id, day, slot, confirmation_status FROM schedule WHERE day = :day AND slot = :slot AND student_id = :student_id AND confirmation_status = :confirmation_status",
                            student_id=student_id, confirmation_status="Booked", day=student_day, slot=student_slot)
        if booked:
            return apology_student("This time has already been booked!")

        # Inserts into the database the selected time slot
        rows = db.execute("INSERT INTO schedule (student_id, day, slot, confirmation_status) VALUES(:student_id, :day, :slot, :confirmation_status)",
                          student_id=student_id, day=student_day, slot=student_slot, confirmation_status="Selected")

        # If "rows" returns an empty list, return apology_student
        if not rows:
            return apology_student("You have already selected that time slot")
        else:

            # Removes the number and dash from the selected day for better visualization
            student_day = request.form.get("student_day")[2:]
            return success_student(f"You have successfully set up a time on {student_day} at {student_slot}")


# Function where the visitor can book a time slot
@app.route("/visitor/book-time", methods=["GET", "POST"])
@login_required
def select_visitor():

    visitor_id = session["user_id"]

    if request.method == "GET":

        # Selects all the available time slots with confirmation_status "Selected" from the database, and stores them in a dictionary "timeslot"
        timeslots = db.execute("SELECT schedule.student_id, day, slot, Fname FROM schedule, student WHERE student.student_id = schedule.student_id GROUP BY schedule.student_id, day, slot HAVING confirmation_status = :confirmation_status",
                               confirmation_status="Selected")

        timeslot_lists = []

        # Loops through the list "timeslots" with each dictionary containing the information regarding the day, slot and the name of the student
        for timeslot in timeslots:
            timeslot_dic = {}
            # Combines the day, slot and the firstname of the student into 1 variable "slot"
            timeslot_dic["slot"] = timeslot['day']+"---"+timeslot['slot']+"---"+timeslot['Fname']
            timeslot_lists.append(timeslot_dic)
        return render_template("visitor/book-time.html", timeslot_lists=timeslot_lists)

    # If the method "POST" is used
    else:

        if not request.form.get("slot"):
            return apology_visitor("You forgot to book a time!")

        day = request.form.get("slot")[0:5]
        slot = request.form.get("slot")[8:13]
        Fname = request.form.get("slot")[16:]

        stud_id = db.execute("SELECT student_id, day, slot FROM schedule WHERE confirmation_status = :confirmation_status",
                             confirmation_status="Selected")

        for i in range(len(stud_id)):
            if stud_id[i].get('day') == day and stud_id[i].get('slot') == slot:
                student_id = stud_id[i].get('student_id')

        time_booked = db.execute(
            "SELECT day, slot, confirmation_status FROM schedule WHERE confirmation_status = :confirmation_status", confirmation_status="Booked")
        if time_booked:
            for i in range(len(time_booked)):
                if time_booked[i].get('day') == day and time_booked[i].get('slot') == slot:
                    return apology_visitor("You have already booked this time with someone else!")

        db.execute(f"UPDATE schedule SET confirmation_status = :confirmation_status, visitor_id = :visitor_id WHERE student_id = :student_id AND day = :day AND slot = :slot",
                   student_id=student_id, visitor_id=visitor_id, confirmation_status="Booked", day=day, slot=slot)

        day = request.form.get("slot")[2:5]
        return success_visitor(f"You have Booked {day} at {slot} with student {Fname}")


# Function where the student can cancel a time slot before it is booked by a visitor
@app.route("/student/cancel-time-slot", methods=["GET", "POST"])
@login_required
def cancel():

    student_id = session["user_id"]

    if request.method == "GET":

        # Selects all the available time slots with confirmation_status "Selected" from the database, and stores them in a dictionary "timeslot"
        timeslots = db.execute("SELECT day, slot FROM schedule GROUP BY student_id, day, slot HAVING student_id = :student_id AND confirmation_status = :confirmation_status",
                               student_id=student_id, confirmation_status="Selected")

        timeslot_lists = []

        for timeslot in timeslots:
            timeslot_dic = {}
            timeslot_dic["slot"] = timeslot['day']+"---"+timeslot['slot']
            timeslot_lists.append(timeslot_dic)
        return render_template("student/cancel-time-slot.html", timeslot_lists=timeslot_lists)

    # If the method "POST" is used
    else:

        if not request.form.get("slot"):
            return apology_student("You haven't selected which time-slot to cancel")
        day = request.form.get("slot")[0:5]
        slot = request.form.get("slot")[8:13]

        # Change the data in the database
        db.execute(f"UPDATE schedule SET confirmation_status = :confirmation_status WHERE student_id = :student_id AND day = :day AND slot = :slot",
                   student_id=student_id, confirmation_status="Slot_cancelled", day=day, slot=slot)
        day = request.form.get("slot")[2:5]
        return success_student(f"You have cancelled your time slot on {day} at {slot}")


# Function where the student can cancel an appointment after a time slot is booked by a visitor
@app.route("/student/cancel-appointment", methods=["GET", "POST"])
@login_required
def cancel_app_student():
    student_id = session["user_id"]

    if request.method == "GET":

        timeslots = db.execute("SELECT day, slot FROM schedule GROUP BY student_id, day, slot HAVING student_id = :student_id AND confirmation_status = :confirmation_status",
                               student_id=student_id, confirmation_status="Booked")

        timeslot_lists = []

        for timeslot in timeslots:
            timeslot_dic = {}
            timeslot_dic["slot"] = timeslot['day']+"---"+timeslot['slot']
            timeslot_lists.append(timeslot_dic)
        return render_template("student/cancel-appointment.html", timeslot_lists=timeslot_lists)

    # If the method "POST" is used
    else:

        if not request.form.get("slot"):
            return apology_student("You forgot to choose which time to cancel!")

        day = request.form.get("slot")[0:5]
        slot = request.form.get("slot")[8:13]

        # change the data in the dbs
        db.execute(f"UPDATE schedule SET confirmation_status = :confirmation_status WHERE student_id = :student_id AND day = :day AND slot = :slot",
                   student_id=student_id, confirmation_status="App_cancelled_stu", day=day, slot=slot)

        day = request.form.get("slot")[2:5]
        return success_student(f"You have cancelled your appointment-'{day}'-'{slot}'")


# Function where the visitor can cancel an appointment after booking it
@app.route("/visitor/cancel-appointment", methods=["GET", "POST"])
@login_required
def cancel_app_visitor():
    visitor_id = session["user_id"]

    if request.method == "GET":

        timeslots = db.execute("SELECT schedule.student_id, day, slot, Fname FROM schedule, student WHERE student.student_id = schedule.student_id GROUP BY schedule.student_id, day, slot HAVING confirmation_status = :confirmation_status",
                               confirmation_status="Booked")

        timeslot_lists = []
        for timeslot in timeslots:
            timeslot_dic = {}
            timeslot_dic["slot"] = timeslot['day']+"---"+timeslot['slot']+"---"+timeslot['Fname']
            timeslot_lists.append(timeslot_dic)
        return render_template("visitor/cancel-appointment.html", timeslot_lists=timeslot_lists)

    # If the method "POST" is used
    else:

        if not request.form.get("slot"):
            return apology_visitor("You forgot to choose which time to cancel!")

        day = request.form.get("slot")[0:5]
        slot = request.form.get("slot")[8:13]
        Fname = request.form.get("slot")[16:]

        stud_id = db.execute("SELECT student_id, day, slot FROM schedule WHERE confirmation_status = :confirmation_status",
                             confirmation_status="Booked")

        for i in range(len(stud_id)):
            if stud_id[i].get('day') == day and stud_id[i].get('slot') == slot:
                student_id = stud_id[i].get('student_id')

        db.execute(f"UPDATE schedule SET confirmation_status = :confirmation_status, visitor_id = :visitor_id WHERE student_id = :student_id AND day = :day AND slot = :slot",
                   student_id=student_id, visitor_id=visitor_id, confirmation_status="Selected", day=day, slot=slot)

        day = request.form.get("slot")[2:5]
        return success_visitor(f"You have cancelled your appointment on {day}, {slot} with student {Fname}")


# From TFs
def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)