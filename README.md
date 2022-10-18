# swisspollen-training

## Docker

If the Dockerfile has been modified, you need to re-build your Docker image using the following command in the swisspollen-training repository:

```bash sudo docker build --no-cache --build-arg HTTP_PROXY=http://proxy.meteoswiss.ch:8080 --build-arg HTTPS_PROXY=http://proxy.meteoswiss.ch:8080 -t <user>/swisspollen-training .```

To start a Docker container and the Jupyter Lab server use the following:

```bash sudo docker run -it --gpus all --rm -v `pwd`:/tf/home/ -p <dest_port>:8888 <user>/swisspollen-training```

Then open your local web browser and connect to the server with address `localhost:<dest_port>`. Note that `<dest_port>` should be forwarded in your SSH connection.