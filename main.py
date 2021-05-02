from flask import Flask, url_for, render_template, redirect, session

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, RadioField
from wtforms.validators import DataRequired


from authlib.integrations.flask_client import OAuth

import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

import random


#initialize flask app
app = Flask(__name__)
app.secret_key = 'random key'

#initialize connection to firebase
cred = credentials.ApplicationDefault()

#initialize the firestore database
db = firestore.client()
batch = db.batch()
user_ref = db.collection('Ghosts')
docs = user_ref.stream()
ghosts = []
for doc in docs:
    ghosts.append(doc.to_dict())

#initialize global variables
email = None
firstName = None
lastName = None
Gname = None
img = None
ghost = None

#initialize OAuth library to gain acces to google sign in
oauth = OAuth(app)



#a login link to take the user to the google sign in page
@app.route('/')
def index():
    global email
    if email == None:
        return render_template('index.html')
    else:
        return redirect(url_for('login'))

@app.route('/login')
def login():
    google = oauth.create_client('google')
    redirect_url = url_for('authorize', _external=True)
    return google.authorize_redirect(redirect_url)

@app.route('/home')
def home():
    global firstName
    global lastName
    global Gname
    #check if the users email is already in the database
    user = emailCheck()
    if(user):
        #retrieve returning users ghost information
        email_ref = user_ref.where(u'email', u'==', email).stream()
        for ref in email_ref:
            info = ref.to_dict()
            break
        Gname = info['ghost']
        firstName = info['firstName']
        lastName = info['lastName']
        return render_template('home.html', user=user, firstName=firstName, Gname=Gname, lastName=lastName)
    else:
        #if no ghost name exist give them a link to chose one
        return render_template('home.html', user=user)

#once the google sign in is authenticated retrieve the users email
@app.route('/authorize')
def authorize():
    global email
    google = oauth.create_client('google')
    token = google.authorize_access_token()
    resp = google.get('userinfo')
    
    userinfo = resp.json()

    email = userinfo['email']

    return redirect('/home')

@app.route('/name', methods=['GET', 'POST'])
def ghost():
    global firstName
    global lastName
    global ghost
    form = LoginForm()
    if form.validate_on_submit():
        firstName = form.firstName._value()
        lastName = form.lastName._value()
        #before loading the choices page select three random ghosts 
        #to be chosen from
        ghost  = random.sample(getFreeGhosts(), k=3)
        return redirect(url_for('choices'))
    return render_template('name.html', form=form)


@app.route('/choices', methods=['GET', 'POST'])
def choices():
    global ghost
    global email
    global Gname
    global firstName
    global lastName
    
    form = GhostForm()
    ghostimg1 = ghost[0]['url']
    ghostname1 = ghost[0]['ghost']
    ghostdesc1 = ghost[0]['description']
    ghostimg2 = ghost[1]['url']
    ghostname2 = ghost[1]['ghost']
    ghostdesc2 = ghost[1]['description']
    ghostimg3 = ghost[2]['url']
    ghostname3 = ghost[2]['ghost']
    ghostdesc3 = ghost[2]['description']
    if form.is_submitted():
        Gname = ghost[int(form.radio.data)-1]['ghost']
        if(emailCheck()):
            #get the reference for users email in database
            email_ref = user_ref.where(u'email', u'==', email).stream()
            for ref in email_ref:
                e_ref = f'{ref.id}'
                break
            #erase any data to any previously related ghost
            batch.update(user_ref.document(e_ref), {u'email' : ''})
            batch.update(user_ref.document(e_ref), {u'firstName': ''})
            batch.update(user_ref.document(e_ref), {u'lastName': ''})

        #get reference for new ghost
        ghost_ref = user_ref.where(u'ghost', u'==', Gname).stream()
        for ref in ghost_ref:
            g_ref = f'{ref.id}'
        #update database
        batch.update(user_ref.document(g_ref), {u'email': email})
        batch.update(user_ref.document(g_ref), {u'firstName': firstName})
        batch.update(user_ref.document(g_ref), {u'lastName': lastName})
        
        #commit updates to database and return to home page
        batch.commit()
        updateData()
        return redirect(url_for('home'))
    else:
        return render_template(
            'choices.html', form=form, 
            ghostimg1=ghostimg1, ghostimg2=ghostimg2, ghostimg3=ghostimg3, 
            ghostname1=ghostname1,ghostname2=ghostname2,ghostname3=ghostname3,
            ghostdesc1=ghostdesc1, ghostdesc2=ghostdesc2, ghostdesc3=ghostdesc3)

#return an array of available ghosts
def getFreeGhosts():
    freeGhosts = []
    for ghost in ghosts:
        if ghost['email'] == '' or ghost['email'] == None:
            freeGhosts.append(ghost)
    return freeGhosts

#see if the logged in user has an email already in the database
def emailCheck():
    check = False
    for ghost in ghosts:
        if ghost['email'] == email:
            check = True
            break
    return check

def updateData():
    user_ref = db.collection('Ghosts')
    docs = user_ref.stream()
    ghosts = []
    for doc in docs:
        ghosts.append(doc.to_dict())



#form for entering first and last name
class LoginForm(FlaskForm):
    firstName = StringField('First Name', validators=[DataRequired()])
    lastName = StringField('Last Name', validators=[DataRequired()])
    submit = SubmitField('Find Ghosts')

#form for selcting ghost
class GhostForm(FlaskForm):
    radio = RadioField('', choices=[("1", "1"),
        ("2", "2"), ("3","3")])
    submit = SubmitField('Choose Ghost')