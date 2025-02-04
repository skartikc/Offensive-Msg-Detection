from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, join_room, leave_room, emit
from flask_session import Session
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from tqdm import tqdm
import pandas as pd

modelr = pickle.load(open("timepass-RF.sav", 'rb'))
df = pd.read_csv("text-vector.csv")
text_vector = df['tokens'].tolist()

app = Flask(__name__)
app.debug = True
app.config['SECRET_KEY'] = 'secret'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)
socketio = SocketIO(app, manage_session=False)


@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')


@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if(request.method == 'POST'):
        username = request.form['username']
        room = request.form['room']
        # Store the data in session
        session['username'] = username
        session['room'] = room
        return render_template('chat.html', session=session)
    else:
        if(session.get('username') is not None):
            return render_template('chat.html', session=session)
        else:
            return redirect(url_for('index'))


@socketio.on('join', namespace='/chat')
def join(message):
    room = session.get('room')
    join_room(room)
    emit('status', {'msg':  session.get('username') +
         ' has entered the room.'}, room=room)


def toVect(a):
    vectorizer = TfidfVectorizer()
    untokenized_data = [''.join(tweet)
                        for tweet in tqdm(text_vector, "Vectorizing...")]
    # print(untokenized_data)
    vectorizer = vectorizer.fit(untokenized_data)
    rev = vectorizer.transform([a])
    # print(rev)
    return rev


@socketio.on('text', namespace='/chat')
def text(message):
    room = session.get('room')
    result = modelr.predict(toVect(message['msg']))
    if 'OFF' in result:
        newmsg = "MESSAGE DELETED DUE ITS OFFENSIVE NATURE"
    else:
        newmsg = message['msg']
    emit('message', {'msg': session.get(
        'username') + ' : ' + newmsg}, room=room)


@socketio.on('left', namespace='/chat')
def left(message):
    room = session.get('room')
    username = session.get('username')
    leave_room(room)
    session.clear()
    emit('status', {'msg': username + ' has left the room.'}, room=room)


if __name__ == '__main__':
    socketio.run(app)
