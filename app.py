from flask import Flask, request, make_response, render_template, jsonify
from GPT import ConversationAPI

srvr = "http://127.0.0.1:5000"
app, gpt_api = Flask(__name__), None
#пока что один объект на всех пользователей приложения с одним общим диалогом на всех
#потом нужно будет или хранить диалог в разрезе пользователей (нагружает сервер), или хранить его на клиенте
# (нагружает канал связи). решим по месту
gpt_api = ConversationAPI()

@app.route('/gpt', methods=['GET'])
@app.route('/gpt/index', methods=['GET'])
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

if __name__ == "__main__":
    app.run(debug=True)