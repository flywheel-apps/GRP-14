# Use the latest Python 3 docker image
FROM bids/freesurfer:v6.0.1-5

MAINTAINER Flywheel <support@flywheel.io>

RUN curl -sL https://deb.nodesource.com/setup_10.x | sudo bash -

RUN apt-get update && \
    apt-get install -y \
    zip && \
    rm -rf /var/lib/apt/lists/* 
# The last line above is to help keep the docker image smaller

RUN pip3 install flywheel-sdk==10.7.4 && \
    rm -rf /root/.cache/pip

# Make directory for flywheel spec (v0)
ENV FLYWHEEL /flywheel/v0
WORKDIR ${FLYWHEEL}

# Save docker environ
ENV PYTHONUNBUFFERED 1
RUN python -c 'import os, json; f = open("/tmp/gear_environ.json", "w"); json.dump(dict(os.environ), f)' 

# Copy executable/manifest to Gear
COPY manifest.json ${FLYWHEEL}/manifest.json
COPY utils ${FLYWHEEL}/utils
COPY freesurfer_tables.pl ${FLYWHEEL}/freesurfer_tables.pl
COPY dry_run_data.tgz ${FLYWHEEL}/dry_run_data.tgz
COPY run.py ${FLYWHEEL}/run.py

# Configure entrypoint
RUN chmod a+x ${FLYWHEEL}/freesurfer_tables.pl
RUN chmod a+x ${FLYWHEEL}/run.py
ENTRYPOINT ["/flywheel/v0/run.py"]
