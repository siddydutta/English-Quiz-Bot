import os
from collections import defaultdict
from datetime import datetime, timedelta

from flask import Flask, request

from bot import send_poll, stop_poll, send_message
from quiz_db import add_poll, get_poll, add_answer, get_active_polls, \
    update_poll_status, get_leaderboard, get_quiz, update_quiz
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)


@app.route('/')
def hello_world():
    return 'App is running'


@app.route('/start-quiz', methods=['GET'])
def start_quiz():
    with app.app_context():
        quiz = get_quiz()
        questions = quiz.get('questions')
        for index, question in enumerate(questions, start=1):
            prompt = f"Question [{index}/{len(questions)}]: {question.get('prompt')}"
            print(prompt)
            result = send_poll(prompt,
                               question.get('options'),
                               question.get('correct_option_id'),
                               question.get('explanation'))
            poll = {
                'poll_id': result.get('poll').get('id'),
                'message_id': result.get('message_id'),
                'correct_option_id': question.get('correct_option_id'),
                'quiz_no': quiz.get('quiz_no'),
                'active': True
            }
            add_poll(poll)
        # update_quiz(quiz)
        quiz_expiration_time = float(os.environ.get('QUIZ_EXPIRATION', 10))
        scheduler.add_job(end_quiz, trigger='date', run_date=datetime.now() + timedelta(hours=quiz_expiration_time),
                          args=[quiz.get('quiz_no')])
        return 'ok', 200


scheduler = BackgroundScheduler()
# TODO Config scheduler
scheduler.add_job(start_quiz, trigger='cron', hour='11', minute='30')
scheduler.start()


@app.route('/stop-quiz', methods=['PUT'])
def stop_quiz():
    return end_quiz(int(request.args.get('quiz_no')))


def end_quiz(quiz_no):
    with app.app_context():
        print("Ending quiz", quiz_no)
        polls = get_active_polls(quiz_no)
        for poll in polls:
            stop_poll(poll.get('message_id'))
        update_poll_status(quiz_no)
        leaderboad(quiz_no)
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


@app.route('/send-leaderboard', methods=['GET'])
def send_leaderboard():
    quiz_no = int(request.args.get('quiz_no'))
    return leaderboad(quiz_no)


def leaderboad(quiz_no):
    results = get_leaderboard(quiz_no)
    print(results)
    score_map = defaultdict(list)
    for result in results:
        username = result.get('username')
        firstname = result.get('firstname')
        score_map[result.get('total_score')].append('@'+username if username else firstname)
    print(score_map)
    five = " ".join(score_map.get(5, []))
    four = " ".join(score_map.get(4, []))
    three = " ".join(score_map.get(3, []))
    text = f"Thank you for participating in today's Daily Quiz! 🥳🎉🎉🎉\n\n" \
           f"🥇 Jobcoachers who got 5/5 Questions correct ⭐⭐⭐⭐⭐:\n" \
           f"{five}\n\n" \
           f"🥈 Jobcoachers who got 4/5 Questions correct ⭐⭐⭐⭐:\n" \
           f"{four}\n\n" \
           f"🥉 Jobcoachers who got 3/5 Questions correct ⭐⭐⭐:\n" \
           f"{three}\n\n" \
           f"Congratulations Jobcoachers! 👏🎊" \
           f"Keep it up and practice more. 📚"
    send_message(text)
    return text, 200


if __name__ == '__main__':
    app.run()
