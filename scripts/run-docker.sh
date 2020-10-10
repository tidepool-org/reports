#!/bin/bash
docker run -it --rm --volume $(pwd)/output:/app/output --name verification_report verification_report
