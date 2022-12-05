import bson

from flask import Flask, request
from flask_swagger_ui import get_swaggerui_blueprint
from quiz_db import get_quiz_questions, update_question, add_poll, get_poll, add_answer, add_quiz_question
from bot import send_poll

app = Flask(__name__)
# START Swagger Specification #
SWAGGER_URL = '/swagger'
API_URL = '/static/swagger.json'
SWAGGERUI_BLUEPRINT = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "English-Quiz-Bot"
    }
)
app.register_blueprint(SWAGGERUI_BLUEPRINT, url_prefix=SWAGGER_URL)
# END Swagger Specification #


@app.route('/')
def hello_world():
    return 'App is running'


@app.route('/add-question', methods=['POST'])
def add_question():
    try:
        add_quiz_question(request.json)
    except:
        return 'not added', 500
    return 'ok', 200


# TODO Should use BackgroundScheduler or cron job to invoke endpoint?
@app.route('/send-quiz')
def send_quiz():
    quiz_id = bson.objectid.ObjectId()
    questions = get_quiz_questions(1)  # TODO Update Limit
    for question in questions:
        poll_id = send_poll(question['question'], question['options'],
                            question['correct_option_id'], question['explanation'])
        # TODO Enable Update Question
        # update_question(question['_id'], poll_id, quiz_id)
        add_poll(poll_id, question['correct_option_id'], quiz_id)
    return 'ok', 200


@app.route('/webhook-poll-answer', methods=['POST'])
def process_poll_answer_update():
    update = request.json
    if 'poll_answer' not in update:
        # Don't process other updates
        return "", 204

    poll_answer = update['poll_answer']

    poll = get_poll(poll_answer['poll_id'])
    is_correct = poll['correct_option'] == poll_answer['option_ids'][0]

    answer = {'poll': poll, 'user': poll_answer['user'], 'is_correct': is_correct}
    add_answer(answer)
    return "", 200


if __name__ == '__main__':
    app.run()
