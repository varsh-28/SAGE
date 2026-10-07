FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV OPSGRAPH_BACKEND=tfidf
RUN python -m opsgraph.cli generate
EXPOSE 8000
CMD ["uvicorn", "opsgraph.api:app", "--host", "0.0.0.0", "--port", "8000"]
