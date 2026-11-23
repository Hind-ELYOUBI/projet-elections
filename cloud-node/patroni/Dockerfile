FROM postgres:16
RUN apt-get update && apt-get install -y --no-install-recommends python3-venv && \
    python3 -m venv /opt/patroni && \
    /opt/patroni/bin/pip install --no-cache-dir "patroni[etcd3]==3.3.2" psycopg2-binary && \
    rm -rf /var/lib/apt/lists/*
COPY patroni.yml seed.sql seed.sh /etc/patroni/
RUN chmod +x /etc/patroni/seed.sh && chown -R postgres /etc/patroni
USER postgres
ENTRYPOINT []
CMD ["/opt/patroni/bin/patroni", "/etc/patroni/patroni.yml"]
