import os
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, request

from bot import send_poll, stop_poll, send_message
from quiz_db import add_poll, get_poll, get_active_polls, \
    update_poll_status, get_quiz, update_quiz, update_quiz_engagement, update_quiz_session, \
    get_quiz_results

app = Flask(__name__)


@app.route('/')
def hello_world():
    return 'English Quiz Bot is running'


@app.route('/start-quiz', methods=['GET'])
def start_quiz():
    with app.app_context():
        quiz = get_quiz()
        if quiz is None:
            return 'no quiz found', 422
        questions = quiz.get('questions')
        if questions is not None:
            send_message("Hey Jobcoachers, here is your quiz for today!")
        for index, question in enumerate(questions, start=1):
            prompt = f"Question [{index}/{len(questions)}]: {question.get('prompt')}"
            result = send_poll(prompt,
                               question.get('options'),
                               question.get('correct_option_id'),
                               question.get('explanation'))
            poll = {
                'quiz_id': quiz.get('_id'),
                'poll_id': result.get('poll').get('id'),
                'message_id': result.get('message_id'),
                'correct_option_id': question.get('correct_option_id'),
                'quiz_no': quiz.get('quiz_no'),
                'question_no': index,
                'active': True
            }
            add_poll(poll)
        update_quiz(quiz)
        quiz_expiration_time = float(os.environ.get('QUIZ_EXPIRATION', 10))
        scheduler.add_job(end_quiz,
                          trigger='date',
                          run_date=datetime.now() + timedelta(hours=quiz_expiration_time),
                          args=[quiz.get('quiz_no')])
        return f"started quiz {quiz.get('quiz_no')}", 200


scheduler = BackgroundScheduler()
# Start a new quiz every day at 4:00 PM IST
scheduler.add_job(start_quiz,
                  trigger='cron',
                  hour=os.environ.get('QUIZ_START_HOUR', 10),
                  minute=os.environ.get('QUIZ_START_MINUTE', 30))
scheduler.start()


@app.route('/stop-quiz', methods=['PUT'])
def stop_quiz():
    return end_quiz(int(request.args.get('quiz_no')))


def end_quiz(quiz_no):
    with app.app_context():
        print("ending quiz", quiz_no)
        polls = get_active_polls(quiz_no)
        for poll in polls:
            stop_poll(poll.get('message_id'))
        update_poll_status(quiz_no)
        print("ended quiz", quiz_no)
        return leaderboad(quiz_no)


@app.route('/webhook-poll-answer', methods=['POST'])
def process_poll_answer_update():
    update = request.json
    if 'poll_answer' not in update:
        # Don't process other updates
        return '', 204

    poll_answer = update['poll_answer']
    poll = get_poll(poll_answer.get('poll_id'))

    selected_option = poll_answer.get('option_ids')[0]
    score = int(poll.get('correct_option_id') == selected_option)  # 1 or 0

    update_quiz_engagement(poll.get('quiz_id'),
                           poll.get('question_no'),
                           score)
    update_quiz_session(poll.get('quiz_id'),
                        poll.get('quiz_no'),
                        poll.get('question_no'),
                        poll_answer.get('user'),
                        score)
    return '', 200


@app.route('/send-leaderboard', methods=['GET'])
def send_leaderboard():
    quiz_no = int(request.args.get('quiz_no'))
    return leaderboad(quiz_no)


def leaderboad(quiz_no):
    results = get_quiz_results(quiz_no)
    score_map = {}
    for result in results:
        users = []
        for user in result.get('users'):
            users.append('@' + user.get('username') if user.get('username') else user.get('first_name', ''))
        score_map[result.get('total_score')] = users

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
    print(text)
    return text, 200


if __name__ == '__main__':
    app.run()
