FROM python:2.7

COPY src/requirements.txt /opt/requirements.txt

RUN pip install -r /opt/requirements.txt

COPY src/icloud-photo-sync.py /opt/

ENTRYPOINT ["/opt/icloud-photo-sync.py"]
