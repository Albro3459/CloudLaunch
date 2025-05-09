# Use AWS Lambda Python base image for x86_64
FROM public.ecr.aws/lambda/python:3.11

# Set working directory inside container
WORKDIR /layer

# Install required packages into /layer/python
RUN pip install --upgrade pip && \
    pip install --no-cache-dir firebase-admin google-cloud-firestore requests qrcode[pil] -t python/