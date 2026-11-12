FROM caddy:2.11.9 AS proxy
FROM python:3.14-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY --from=proxy /usr/bin/caddy /usr/local/bin/caddy
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home --uid 10001 studio \
    && mkdir -p /data/studio && chown -R studio:studio /data
COPY server.py generation.py artifacts.py studio.py ./
COPY minhwa_workflow/__init__.py minhwa_workflow/workflow.py ./minhwa_workflow/
COPY minhwa_workflow/garden-anchors ./minhwa_workflow/garden-anchors/
COPY fonts ./fonts/
COPY hosted_web ./hosted_web/
COPY deploy/Caddyfile deploy/start.py ./deploy/
USER studio
EXPOSE 10000
CMD ["python", "deploy/start.py"]
