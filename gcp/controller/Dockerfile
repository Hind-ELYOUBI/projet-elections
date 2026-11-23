FROM python:3.12-slim
RUN pip install --no-cache-dir flask==3.1.0
COPY controller.py /controller.py
CMD ["python", "-u", "/controller.py"]
