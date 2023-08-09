FROM python:3.10-slim
WORKDIR /Projects/Enhanced_GPT_Conversation
COPY . .
RUN pip install -r requirements.txt
EXPOSE 4999
ENV FLASK_APP=app.py
CMD ["flask", "run", "--host=0.0.0.0", "--port=4999"]