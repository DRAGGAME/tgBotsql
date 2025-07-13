#!/bin/bash
sudo docker stop tgadm; sudo docker rm tgadm; sudo docker  image rm user/tgadm:latest
sudo docker build -t user/tgadm:latest .
docker run -e TG_API=key -e ip=127.0.0.1 -e DATABASE=database -e user=user -e password=password -d --restart=always --network=host --name tgadm <user>tgadm:latest
