from flask import Flask, request, make_response, render_template, jsonify, send_file
from GPT import ConversationAPI
from threading import Thread
from pathlib import Path
from json import load
import webbrowser, requests, time

app_settings_file, srvr = Path(__file__).resolve().parent / 'settings/app_settings.json', f"http://127.0.0.1"
app, gpt_api = Flask(__name__), None
#пока что один объект на всех пользователей приложения с одним общим диалогом на всех
#потом нужно будет или хранить диалог в разрезе пользователей (нагружает сервер), или хранить его на клиенте
# (нагружает канал связи). решим по месту
gpt_api = ConversationAPI()

@app.route('/gpt/ping', methods=['GET'])
def ping():
    return 'Enhanced GPT conversation is working'

@app.route('/gpt', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/gpt/get_conversation_cash', methods=['GET'])
def get_converation_cash():
    return jsonify(gpt_api.conversation)

@app.route('/gpt/send_message', methods=['POST'])
def send_message():
    try:
        message_data = request.get_json(force=True)
    except:
        return make_response({'error_type':'Other error', 'description':'Invalid request data'}, 400)
    response = gpt_api.send_message(role=message_data['role'], content=message_data['content'])
    status = 200 if response['success'] else 400
    return make_response(response['result'], status)

@app.route('/gpt/get_openai_key', methods = ['GET'])
def get_openai_key():
    return gpt_api.openai_key

@app.route('/gpt/set_openai_key', methods=['POST'])
def set_openai_key():
    #add error checking later
    gpt_api.openai_key = request.get_data(as_text=True)
    return make_response('Ok', 200)

@app.route('/gpt/conversation_test', methods=['GET'])
def open_conversation_test():
    return send_file('static/lib/voiceTalking/speech_recognition_test.html')

def _read_settings() -> dict:
    with open(app_settings_file, 'r') as file:
       app_settings = load(file)
    return app_settings

def _open_ui(port, **kwargs):
    while True:
        time.sleep(1)
        result = requests.get(f'{srvr}:{port}/gpt/ping')
        if result.status_code == 200:
            webbrowser.open_new_tab(f'{srvr}:{port}/gpt')
            break

if __name__ == "__main__":
    app_settings = _read_settings()
    ui_thread = Thread(target=_open_ui, kwargs=app_settings)
    ui_thread.start()
    app.run(**app_settings)