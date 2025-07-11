FROM continuumio/miniconda3:latest

LABEL main='Draggame'

WORKDIR /app

COPY . /app

RUN conda update conda \
    && conda env create -f telegrambot.yml \
    && echo "conda activate telegramBotsAdm" > ~/.bashrc \
    && conda clean -afy

ENV PATH=/opt/conda/envs/telegramBotsAdm/bin:$PATH

EXPOSE 5432

CMD ["python", "run.py"]
