FROM python:3.7

WORKDIR /usr/src/app

COPY pdflinks/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

ENV FLASK_APP=app.py
ENV FLASK_ENV=production

EXPOSE 8000

COPY pdflinks/ .
CMD ["flask", "run" ,"--host=0.0.0.0", "--port=8000"]
