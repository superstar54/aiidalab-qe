# syntax=docker/dockerfile:1
FROM aiidalab/qe:amd64-latest

# Switch to root user to change permissions
USER root

# Make all scripts in /usr/local/bin/before-notebook.d executable
RUN chmod +x /usr/local/bin/before-notebook.d/*

# pg_ctl: cannot be run as root
USER ${NB_USER}
# Run all scripts in the /usr/local/bin/before-notebook.d directory
RUN for script in /usr/local/bin/before-notebook.d/*; do \
        if [ -x "$script" ]; then \
            "$script"; \
        fi \
    done


# Stop services for RabbitMQ and PostgreSQL
# RUN mamba run -n aiida-core-services pg_ctl -w -D /home/${NB_USER}/.postgresql stop
# RUN mamba run -n aiida-core-services rabbitmq-server stop

# Stop Aiida daemon
RUN verdi daemon stop


USER root

# tar home folder to /opt/home.tar
RUN tar -cf /opt/home.tar /home/${NB_USER}

# Copy 00_untar_home.sh to /usr/local/bin/before-notebook.d
COPY 00_untar_home.sh /usr/local/bin/before-notebook.d/

# Ensure the script is executable
RUN chmod +x /usr/local/bin/before-notebook.d/00_untar_home.sh

# Rm /home/${NB_USER}
RUN rm -rf /home/${NB_USER}

USER ${NB_USER}

WORKDIR "/home/${NB_USER}"
