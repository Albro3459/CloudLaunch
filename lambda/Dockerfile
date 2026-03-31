# Cloudlaunch layer with Firebase, Requests, QR Code, and OCI SDK libraries
# So big, that it has to be uploaded to S3 to be used by the Lambdas

# Use AWS Lambda Python base image for x86_64
FROM public.ecr.aws/lambda/python:3.11

# Set working directory inside container
WORKDIR /layer

# Install required packages into /layer/python
RUN pip install --upgrade pip && \
    pip install --no-cache-dir firebase-admin google-cloud-firestore requests qrcode[pil] oci -t python/
