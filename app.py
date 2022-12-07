import bson

from flask import Flask, request
from flask_swagger_ui import get_swaggerui_blueprint
from datetime import datetime
from quiz_db import get_quiz_questions, add_poll, get_poll, add_answer, add_quiz_question
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
    except Exception as e:
        print(e)
        return 'not added', 500
    return 'ok', 200


@app.route('/send-quiz', methods=['GET'])
def send_quiz():
    quiz_no = int(request.args.get("quiz_no"))
    questions = get_quiz_questions(quiz_no)
    for question in questions:
        poll_id = send_poll(question.get('question'), question.get('options'), question.get('correct_option_id'),
                            question.get('explanation'))
        add_poll(poll_id, question['correct_option_id'], quiz_no)
    return 'ok', 200


@app.route('/webhook-poll-answer', methods=['POST'])
def process_poll_answer_update():
    update = request.json
    if 'poll_answer' not in update:
        # Don't process other updates
        return "", 204

    poll_answer = update['poll_answer']
    poll = get_poll(poll_answer.get('poll_id'))

    selected_option = poll_answer.get('option_ids')[0]
    score = int(poll.get('correct_option_id') == selected_option)

    answer = {'poll_id': poll.get('poll_id'),
              'quiz_no': poll.get('quiz_no'),
              'user': poll_answer.get('user'),
              'selected_option': selected_option,
              'score': score,
              'answered': datetime.utcnow()}
    add_answer(answer)
    return "", 200


if __name__ == '__main__':
    app.run()
