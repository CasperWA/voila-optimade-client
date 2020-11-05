FROM python:3.8

WORKDIR /app

COPY requirements*.txt setup.py README.md OPTIMADE-Client.ipynb ./
COPY optimade_client ./optimade_client
RUN pip install -e .[server]

EXPOSE ${PORT}
