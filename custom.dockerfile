ARG AA_DOCKER_TAG
FROM $AA_DOCKER_TAG

WORKDIR ${AUTH_HOME}

COPY /conf/requirements.txt requirements.txt
RUN --mount=type=cache,target=~/.cache \
    pip install -r requirements.txt

# Writable dirs for the SQLite database and logs. Created as the allianceauth user
# (uid 61000) so the named volume mounted at data/ inherits the correct ownership.
RUN mkdir -p ${AUTH_HOME}/myauth/data ${AUTH_HOME}/myauth/log
