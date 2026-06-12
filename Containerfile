FROM registry.fedoraproject.org/fedora:44

RUN dnf install -y python3-pip gcc python3-devel

WORKDIR /opt/llm-katan

COPY llm_katan /opt/llm-katan/llm_katan
COPY pyproject.toml /opt/llm-katan

RUN pip install .

COPY . .

ENTRYPOINT ["llm-katan"]
