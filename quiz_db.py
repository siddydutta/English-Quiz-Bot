import os

from flask import current_app, g
from werkzeug.local import LocalProxy
from flask_pymongo import PyMongo
from datetime import datetime


def get_db():
    """
    Configuration method to return db instance
    """
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = PyMongo(current_app, os.environ.get('MONGO_QUIZ_URI')).db
    return db


# Use LocalProxy to read the global db instance with just `db`
db = LocalProxy(get_db)


def get_quiz_questions(quiz_no: int):
    return [question for question in db.questions.find({'quiz_no': quiz_no})]


def add_quiz_question(question):
    db.questions.insert_one(question)


def add_poll(poll_id, correct_option_id, quiz_no):
    poll = {'poll_id': poll_id, 'correct_option_id': correct_option_id, 'quiz_no': quiz_no, 'posted': datetime.utcnow()}
    db.polls.insert_one(poll)


def get_poll(poll_id):
    return db.polls.find_one({'poll_id': poll_id})


def add_answer(answer):
    db.answers.insert_one(answer)
