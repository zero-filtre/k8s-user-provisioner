FROM python:3.10

WORKDIR /app

COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt \
# Install OpenTelemetry dependencies
&& pip install opentelemetry-distro opentelemetry-exporter-otlp \
# Create the auto instrumentation script
&& opentelemetry-bootstrap -a install

EXPOSE 5000


ENV OTEL_SERVICE_NAME=zerofiltre-provisioner-k8slive\
    OTEL_EXPORTER_OTLP_PROTOCOL=grpc \
    OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED=true \
    OTEL_EXPORTER_OTLP_ENDPOINT=http://otelcol-opentelemetry-collector.zerofiltre-bootcamp.svc.cluster.local:4317

ENTRYPOINT ["opentelemetry-instrument", "python", "run.py"]
