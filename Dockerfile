FROM python:2.7-slim

RUN pip install pyicloud hachoir-parser hachoir-metadata hachoir-core pyyaml

COPY src/icloud-photo-sync.py /opt/

ENTRYPOINT ["/opt/icloud-photo-sync.py"]
