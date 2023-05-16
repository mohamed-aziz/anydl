# Define function directory
ARG FUNCTION_DIR="/function"

FROM python:3.9-bullseye as build-image

# Install aws-lambda-cpp build dependencies
RUN apt-get update && \
  apt-get install -y \
  g++ \
  make \
  cmake \
  unzip \
  libcurl4-openssl-dev

# Include global arg in this stage of the build
ARG FUNCTION_DIR
# Create function directory
RUN mkdir -p ${FUNCTION_DIR}

# Install the runtime interface client
RUN pip install \
        --target ${FUNCTION_DIR} \
        awslambdaric

# Multi-stage build: grab a fresh copy of the base image
FROM python:3.9-bullseye

# Include global arg in this stage of the build
ARG FUNCTION_DIR
# Set working directory to function root directory
WORKDIR ${FUNCTION_DIR}

# Copy in the build image dependencies
COPY --from=build-image ${FUNCTION_DIR} ${FUNCTION_DIR}

COPY entry.sh /entry.sh
ADD aws-lambda-rie /usr/bin/aws-lambda-rie
RUN chmod 755 /entry.sh /usr/bin/aws-lambda-rie

COPY requirements.txt ./
RUN python -m pip install -r requirements.txt --target ${FUNCTION_DIR}

RUN mkdir /app/
ENV PLAYWRIGHT_BROWSERS_PATH "/app/ms-playwright"
RUN apt-get update && apt-get install -y gconf-service libasound2 libatk1.0-0 libcairo2 libcups2 libfontconfig1 libgdk-pixbuf2.0-0 libgtk-3-0 libnspr4 libpango-1.0-0 libxss1 fonts-liberation libappindicator1 libnss3 lsb-release xdg-utils libgstreamer1.0-dev libwoff1 libopus0 libharfbuzz-icu0 libgstreamer-plugins-base1.0-0 libgstreamer-gl1.0-0 libgstreamer-plugins-bad1.0-0 libenchant-2-2 libsecret-1-0 libhyphen0 libwayland-server0 libmanette-0.2-0 libflite1 libgbm1 libgles2 libx264-dev
RUN PYTHONPATH="/function" /function/bin/playwright install
RUN apt-get install -y ffmpeg
COPY app.py ${FUNCTION_DIR}/app.py

EXPOSE 8080
ENTRYPOINT [ "/entry.sh" ]
CMD ["app.lambda_handler"]
