from datetime import datetime

from flask import Flask, request
from flask_swagger_ui import get_swaggerui_blueprint

from bot import send_poll, stop_poll, send_message
from quiz_db import get_quiz_questions, add_poll, get_poll, add_answer, add_quiz_question, get_active_polls, \
    update_poll_status, get_leaderboard

app = Flask(__name__)

# START Swagger Specification #
SWAGGER_URL = '/swagger'
API_URL = '/static/swagger.json'
SWAGGERUI_BLUEPRINT = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': 'English-Quiz-Bot'
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


@app.route('/start-quiz', methods=['GET'])
def start_quiz():
    quiz_no = int(request.args.get('quiz_no'))
    questions = get_quiz_questions(quiz_no)
    for question in questions:
        result = send_poll(question.get('question'), question.get('options'), question.get('correct_option_id'),
                           question.get('explanation'))
        poll = {'poll_id': result.get('poll').get('id'),
                'message_id': result.get('message_id'),
                'correct_option_id': question.get('correct_option_id'),
                'quiz_no': quiz_no,
                'posted': datetime.utcnow(),
                'active': True}
        add_poll(poll)
    return 'ok', 200


@app.route('/stop-quiz', methods=['PUT'])
def stop_quiz():
    quiz_no = int(request.args.get('quiz_no'))
    polls = get_active_polls(quiz_no)
    for poll in polls:
        stop_poll(poll.get('message_id'))
    update_poll_status(quiz_no)
    return '', 200


@app.route('/webhook-poll-answer', methods=['POST'])
def process_poll_answer_update():
    update = request.json
    if 'poll_answer' not in update:
        # Don't process other updates
        return '', 204

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
    return '', 200


@app.route('/leaderboard', methods=['GET'])
def leaderboard():
    quiz_no = int(request.args.get('quiz_no'))
    results = get_leaderboard(quiz_no)
    text = f"Leaderboard for Quiz: {quiz_no}\n"
    for index, result in enumerate(results, start=1):
        text += f"{index}. {result.get('name')}\t{result.get('total_score')}\n"
    send_message(text)
    return text, 200


if __name__ == '__main__':
    app.run()
