FROM n8nio/n8n:latest

USER root
COPY n8n/entrypoint.sh /custom-entrypoint.sh
RUN sed -i 's/\r$//' /custom-entrypoint.sh && chmod +x /custom-entrypoint.sh

USER node
ENTRYPOINT ["/custom-entrypoint.sh"]
