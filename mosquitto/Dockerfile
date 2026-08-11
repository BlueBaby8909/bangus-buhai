FROM eclipse-mosquitto:latest

# Copy the config folder directly into the image
COPY ./config /mosquitto/config

# Fix the permissions so the mosquitto internal user can read the password file
RUN chown -R mosquitto:mosquitto /mosquitto/config && \
    chmod 0700 /mosquitto/config/passwd
