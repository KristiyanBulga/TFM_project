FROM public.ecr.aws/lambda/python:3.9
COPY ./requirements.txt .
RUN pip install --force-reinstall -r requirements.txt
COPY ./functions/process_data.py ./functions/process_data.py
COPY ./utils ./utils