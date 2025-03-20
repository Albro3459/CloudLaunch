# Use AWS Lambda's Python base image
FROM public.ecr.aws/lambda/python:3.8

# Install dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir firebase-admin boto3

# Copy the Lambda function
COPY lambda_function.py ${LAMBDA_TASK_ROOT}

# Set the Lambda function entry point
CMD ["lambda_function.lambda_handler"]
