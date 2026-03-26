FROM artifactory.itg.ti.com/docker-public-local/python:3.13.5-slim

WORKDIR /leaduploadapp

#copy the app file
COPY app.py .
COPY requirements.txt .
COPY ti_stk_2c_pos_rgb.svg .
# copy .streamlit folder
COPY .streamlit ./.streamlit

# set proxy environment variables
# This is required to access the internet from within the container and pip install or uv install
ENV HTTP_PROXY="http://webproxy.ext.ti.com:80"
ENV HTTPS_PROXY="http://webproxy.ext.ti.com:80"
ENV http_proxy="http://webproxy.ext.ti.com:80"
ENV https_proxy="http://webproxy.ext.ti.com:80"
# ENV no_proxy="localhost,127.0.0.1"

# Install dependencies
RUN apt-get update && \
    apt-get install -y git && \
    which git && \
    git --version

# Install dependencies using uv
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

ENV PATH="/root/.local/bin:${PATH}"

CMD ["/bin/bash", "-c", "source .venv/bin/activate && streamlit run app.py --server.port=8501 --server.address=0.0.0.0"]