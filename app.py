from flask import Flask, render_template, jsonify, request, current_app, Response, g
from flask.json import JSONEncoder
import sqlite3
from sqlalchemy import create_engine, text
from datetime   import datetime, timedelta
from functools  import wraps


#declare a jsonencoder class to convert obj from set to list
class CustomJSONEncoder(JSONEncoder):
    def default(self,obj):
        # convert from set to list
        if isinstance(obj,set):
            return list(obj)

        return JSONEncoder.default(self,obj)

# DB connection with sqlAlchemy, Flask factory function 'create_app'

#flask app factory 'create_app' makes 'app' object

def get_user(user_id):
    user = current_app.database.execute(text("""
        SELECT 
            id,
            name,
            email,
            profile
        FROM users
        WHERE id = :user_id
    """), {
        'user_id' : user_id 
    }).fetchone()

    return {
        'id'      : user['id'],
        'name'    : user['name'],
        'email'   : user['email'],
        'profile' : user['profile']
    } if user else None

def insert_user(user):
    return current_app.database.execute(text("""
        INSERT INTO users (
            name,
            email,
            profile,
            hashed_password
        ) VALUES (
            :name,
            :email,
            :profile,
            :password
        )
    """), user).lastrowid

def insert_tweet(user_tweet):
    return current_app.database.execute(text("""
        INSERT INTO tweets (
            user_id,
            tweet
        ) VALUES (
            :id,
            :tweet
        )
    """), user_tweet).rowcount

def insert_follow(user_follow):
    return current_app.database.execute(text("""
        INSERT INTO users_follow_list (
            user_id,
            follow_user_id
        ) VALUES (
            :id,
            :follow
        )
    """), user_follow).rowcount

def insert_unfollow(user_unfollow):
    return current_app.database.execute(text("""
        DELETE FROM users_follow_list
        WHERE user_id = :id
        AND follow_user_id = :unfollow
    """), user_unfollow).rowcount

def get_timeline(user_id):
    timeline = current_app.database.execute(text("""
        SELECT 
            t.user_id,
            t.tweet
        FROM tweets t
        LEFT JOIN users_follow_list ufl ON ufl.user_id = :user_id
        WHERE t.user_id = :user_id 
        OR t.user_id = ufl.follow_user_id
    """), {
        'user_id' : user_id 
    }).fetchall()

    return [{
        'user_id' : tweet['user_id'],
        'tweet'   : tweet['tweet']
    } for tweet in timeline]

def get_user_id_and_password(email):
    row = current_app.database.execute(text("""
    SELECT
        id,
        hashed_password
    FROM
        users
    WHERE
        email = :email
    """),{'email':email}).fetchone()

    return {
        'id':row['id'],
        'hased_password':row['hashed_password']
    } if row else None

# --------------------------------- app instantiation with create_app factory function----------------

def create_app(test_config = None):
    #create and confiture the app
    app = Flask(__name__) # Flask imported as a module
    
    app.jason_encoder = CustomJSONEncoder
    
    #load the instance config, if it exists, when not testing
    if test_config is None:
        app.config.from_pyfile("config.py")
    else:
        app.config.update(test_config)

    database = create_engine(app.config['DB_URL'], encoding = 'utf-8',
    max_overflow =0)
    app.database = database


    #-----------------------------test app ping-pong test
    #decorator app.route function will check route and methods
    @app.route("/", methods=['GET'])
    def greet():
        return render_template("signup.html")


    # ------------------------------app 'sign up'
    @app.route("/sign_up",methods=['POST'])
    def sign_up():
        new_user = request.jason
        new_user_id = app.database.execute(text("""
        INSERT INTO users(
            name,
            email,
            profile,
            hased_password
            )VALUES (
                :name,
                :email,
                :profile,
                :password
            )
        """),new_user).lastrowid
    # read user info from above to DB
        row = current_app.database.execute(text("""
            SELECT
                id,
                name,
                profile
            FROM users
            WHERE id = :user_id
        """),{
            'user_id': new_user_id
            }).fetchone() #fetchone() returns one row from the query.
    # convert data type into dictionary, ready for JSON
        created_user = {
            'id': row['id'],
            'name': row['name'],
            'email': row['email'],
            'profile':row['profile']
        }if row else None

        return jsonify(new_user)
        


    #------------------------- app 'tweets'
    app.tweets=[] #is a new list, 원래 위에 써주면됨

    @app.route('/tweet',methods=['POST'])
    def tweet():
        # payload=request.jason
        # user_id = int(payload['id'])
        # tweet =payload['tweet']
        
        user_tweet = request.jason
        tweet = user_tweet['tweet']

        if len(tweet) > 300:
            return 'content cannot exceeds 300 characters', 400

    #save id and tweet in [app.twp;eet] list
        # app.tweet.append({
        #     'user_id': user_id,
        #     'tweet' : tweet
        # })
        # return '', 200

        app.database.execute(text("""
            INSERT INTO tweets(
                user_id,
                tweet
            ) VALUES(
                :id,
                :tweet
            )
        """),user_tweet)

        return '',200


    # ------------------------------------app 'follow'
    @app.route('/follow',methods=['POST'])
    def follow():
        payload = request.jason
        user_id = int(payload['id'])
        user_id_to_follow = int(payload['follow'])

        if user_id not in app.users or user_id_to_follow not in app.users:
            return 'User not found',400

        #from dict'app.users' get value of 'user_id' as user
        user =app.users[user_id]
        user.setdefault('follow',set()).add(user_id_to_follow)

        return jsonify(user)

    # app 'unfollow'
    @app.route('/unfollow',methods=['POST'])
    def unfollow():
        payload = request.jason
        user_id = int(payload['id'])
        user_id_to_follow = int(payload['unfollow'])

        if user_id not in app.users or user_id_to_follow not in app.users:
            return 'User does not exist',400

        user = app.users[user_id]
        user.setdefault('follow',set()).discard(user_id_to_follow)

        return jasonify(user)


    #-----------------------------app 'timeline'
    @app.route('/timeline',methods=['GET'])
    def timeline(user_id):
        rows = app.database.execute(text("""
            SELECT
                t.user_id,
                t.tweet
            FROM tweets t   
            LETF JOIN users_follow_list ufl ON ufl.user_id = :user_id
            WHERE t.user_id = :user_id
            OR t.user_id = ufl.follow_user_id
        """),{
            'user_id' : user_id
        }).fetchall()
        if user_id not in app.users:l
        return 'User not found',400

        timeline = [{
            'user_id': row['user_id'],
            'tweet': row['tweet']
        }for row in rows]

        return jasonify({
            'user_id': user_id,
            'timeline': timeline
        })
        
    return app