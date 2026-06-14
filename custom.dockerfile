ARG AA_DOCKER_TAG
FROM $AA_DOCKER_TAG

WORKDIR ${AUTH_HOME}

COPY aa-testsite/conf/requirements.txt requirements.txt
RUN --mount=type=cache,target=~/.cache \
    pip install -r requirements.txt

# Local plugin under test: copy the sibling source in and editable-install it so
# its dependencies are baked into the image. docker-compose.yml bind-mounts the
# live host source over this same path, so source edits are picked up on restart.
COPY --chown=allianceauth:allianceauth aa-whatax aa-whatax
RUN --mount=type=cache,target=~/.cache \
    pip install -e aa-whatax

# Writable dirs for the SQLite database and logs. Created as the allianceauth user
# (uid 61000) so the named volume mounted at data/ inherits the correct ownership.
RUN mkdir -p ${AUTH_HOME}/myauth/data ${AUTH_HOME}/myauth/log
