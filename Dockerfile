FROM python:3.8-alpine

LABEL maintainer="Tapani Otala <tapani@tidepool.org>" \
      organization="Tidepool Project" \
      description="Package for producing Tidepool Loop 1.0 Verification Test Report" \
      version="1.0"

COPY requirements.txt /
RUN pip install --no-cache-dir --prefer-binary --compile -r /requirements.txt

WORKDIR /app
COPY ./ ./

CMD [ "python", "./report.py", "--excel" ]
