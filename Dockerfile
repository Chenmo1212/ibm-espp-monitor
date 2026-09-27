FROM python:3.13-slim

WORKDIR /app

# Ensure security non-root user
RUN useradd -m -u 1001 appuser

# Set environment
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

COPY config/ config/
COPY data/ data_default/
COPY src/ src/

# Create data directory permissions for persistent volume
RUN mkdir -p /app/data && chown -R appuser:appuser /app

USER 1001

CMD ["python3", "-m", "ibm_espp_monitor.scheduler"]
