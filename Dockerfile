# ===== BUILDER STAGE =====
FROM python:3.11-slim-bookworm as builder


WORKDIR /app
COPY requirements.txt .

RUN pip install --user --no-cache-dir -r requirements.txt


# ===== RUNTIME STAGE =====
FROM python:3.11-slim-bookworm

WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .

# Set Streamlit config for external access
ENV PATH=/root/.local/bin:$PATH \
    STREAMLIT_SERVER_ENABLE_CORS=false \
    STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Streamlit listens on 8501 by default, expose for Fly.io
EXPOSE 8501

# Default command
CMD ["streamlit", "run", "Procurement_Calculator.py"]
