import os

from flask import current_app, g
from werkzeug.local import LocalProxy
from flask_pymongo import PyMongo
from datetime import datetime


def get_db():
    """
    Configuration method to return db instance
    """
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = PyMongo(current_app, os.environ.get('MONGO_QUIZ_URI')).db
    return db


# Use LocalProxy to read the global db instance with just `db`
db = LocalProxy(get_db)


def get_quiz_questions(quiz_no: int):
    return [question for question in db.questions.find({'quiz_no': quiz_no})]


def add_quiz_question(question):
    db.questions.insert_one(question)


def add_poll(poll):
    db.polls.insert_one(poll)


def get_poll(poll_id):
    return db.polls.find_one({'poll_id': poll_id})


def get_active_polls(quiz_no: int):
    return [poll for poll in db.polls.find({'quiz_no': quiz_no, 'active': True})]


def update_poll_status(quiz_no: int):
    db.polls.update_many({'quiz_no': quiz_no, 'active': True}, {'$set': {'stopped': datetime.utcnow(),
                                                                         'active': False}}, upsert=False)


def add_answer(answer):
    db.answers.insert_one(answer)


def get_leaderboard(quiz_no: int):
    return [score for score in db.answers.aggregate([
        {
            '$match': {
                'quiz_no': quiz_no
            }
        }, {
            '$group': {
                '_id': '$user.id',
                'total_score': {
                    '$sum': '$score'
                },
                'name': {
                    '$first': '$user.first_name'
                }
            }
        }, {
            '$sort': {
                'total_score': -1
            }
        }, {
            '$limit': 3
        }
    ])]
