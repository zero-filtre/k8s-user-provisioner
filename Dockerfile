FROM python:3.10

WORKDIR /app

ARG PROFILE=dev

COPY requirements.txt /app/
COPY . /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install OpenTelemetry dependencies
RUN pip install opentelemetry-api opentelemetry-distro opentelemetry-exporter-otlp opentelemetry-instrumentation-flask
RUN opentelemetry-bootstrap -a install

# Make sure entrypoint.sh is executable
RUN chmod 755 entrypoint.sh

EXPOSE 5000

# Set environment variables for OpenTelemetry (https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/logging/logging.html)
ENV OTEL_SERVICE_NAME=sandbox-provisioner-${PROFILE}

ENV OTEL_PYTHON_LOG_CORRELATION=true
ENV OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED=true
ENV OTEL_PYHTON_LOG_LEVEL=debug

ENV OTEL_LOGS_EXPORTER=otlp

ENV OTEL_TRACES_EXPORTER=otlp
ENV OTEL_METRICS_EXPORTER=otlp

ENV OTEL_EXPORTER_OTLP_ENDPOINT=http://otelcol-opentelemetry-collector.monitoring.svc.cluster.local:4317

# Set entrypoint
ENTRYPOINT ["./entrypoint.sh"]
