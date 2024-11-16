FROM nvidia/cuda:11.8.0-cudnn8-devel-ubuntu22.04
ARG DEBIAN_FRONTEND=noninteractive

RUN mkdir -p /opt/doodle2img
WORKDIR /opt/doodle2img

COPY requirements.txt requirements.txt
RUN apt-get update
RUN apt-get install -y python3-pip
RUN pip3 install torch torchvision torchaudio
RUN pip3 install -r requirements.txt
