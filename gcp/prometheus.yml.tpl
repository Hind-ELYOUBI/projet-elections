global:
  scrape_interval: 5s
  evaluation_interval: 5s
rule_files: [/etc/prometheus/alerts.yml]
alerting:
  alertmanagers:
    - static_configs: [{targets: ["localhost:9093"]}]
scrape_configs:
  - job_name: node
    static_configs:
      - {targets: ["${AZURE_IP}:9100"], labels: {cloud: azure}}
      - {targets: ["${ORACLE_IP}:9100"], labels: {cloud: oracle}}
  - job_name: patroni
    static_configs:
      - {targets: ["${AZURE_IP}:8008"], labels: {cloud: azure}}
      - {targets: ["${ORACLE_IP}:8008"], labels: {cloud: oracle}}
  - job_name: cloudapi
    metrics_path: /metrics/
    static_configs:
      - {targets: ["${AZURE_IP}:8000"], labels: {cloud: azure}}
      - {targets: ["${ORACLE_IP}:8000"], labels: {cloud: oracle}}
  - job_name: apps
    static_configs:
      - {targets: ["${AZURE_IP}:9201", "${AZURE_IP}:9202"], labels: {cloud: azure}}
      - {targets: ["${ORACLE_IP}:9201", "${ORACLE_IP}:9202"], labels: {cloud: oracle}}
  - job_name: controller
    static_configs: [{targets: ["localhost:5000"]}]
