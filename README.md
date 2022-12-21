# swisspollen-training

## SSH

SSH config example:
```
Host gpu3-nb
  HostName 10.182.128.114
  User <user>
  ServerAliveInterval 60
  IdentityFile C:\Users\<user>\.ssh\id_rsa
  LocalForward <dest_port> 127.0.0.1:<dest_port>
  LocalForward <dest_port2> 127.0.0.1:<dest_port2>
```

where `<dest_port>` is the port you'll use to access Jupyter Lab, and `<dest_port2>` is the one you'll use to access TensorBoard.

## Docker

If the Dockerfile has been modified, you need to re-build your Docker image using the following command in the swisspollen-training repository:

```docker build --no-cache --build-arg HTTP_PROXY=http://proxy.meteoswiss.ch:8080 --build-arg HTTPS_PROXY=http://proxy.meteoswiss.ch:8080 -t <user>/swisspollen-training .```

Use the following to start a Docker container and the Jupyter Lab server:

```docker run -it --gpus all --rm -v `pwd`:/tf/home/ -p <dest_port>:8888 -p <dest_port2>:6006 <user>/swisspollen-training```

Then open your local web browser and connect to the server with address `localhost:<dest_port>`. Note that `<dest_port>` should be forwarded in your SSH connection.

## MySQL config file

To connect to the MySQL database, you need to setup a config file using [this utility tool](https://dev.mysql.com/doc/refman/8.0/en/mysql-config-editor.html).
An example of what the command could look like would be:

```mysql_config_editor set --login-path=client --host=10.0.0.10 --port=3306 --user=root --password```

This generates a file that you have to name `.mylogin.cnf` and move to the `config/` folder.

## Swisens dependencies disclaimer

This project requires three external dependencies:
- [CharPyLS](https://github.com/Who8MyLunch/CharPyLS)
- [poleno-db-interface](https://gitlab.swisensdata.ch/swisens/poleno/software/poleno-db-interface)
- [poleno-ml](https://gitlab.swisensdata.ch/swisens/poleno/software/poleno-ml)

The code of CharPyLS is static in the `dependencies/` folder. The code of the two Swisens dependencies is NOT pushed on this repository. They are both "submodules" which means cloning this GitHub repository should recursively clone the two submodules.

<u>BUT</u> changes were made to the poleno-ml code (in `GPU3:/scratch/chg/swisspollen-training/`). Ideally, those changes should be submitted to Swisens through a pull request. They could then review the modifications before accepting and merging them to the main branch. These changes are necessary to run the training and validation code so it's essential to not override them until they're pushed to Swisens' GitLab.

A quick note about modification of these dependencies' code. If modifying these codes from the Docker container, you'll need to make the changes to the /tmp/<dependency>/ files for them to take effect (and probably re-run a !pip install from the code). For these modifications to be saved after the container is killed, duplicate them to the dependencies/<dependency>/ files.

## Docker container's file structure

```
/tf
├── home
│   ├── Dockerfile
│   ├── README.md
│   ├── config
│   │   ├── .mylogin.cnf
│   │   ├── jupyter_lab_config.py
│   │   ├── plugin.jupyterlab-settings
│   │   ├── themes.jupyterlab-settings
│   │   └── tracker.jupyterlab-settings
│   ├── dependencies
│   │   ├── CharPyLS-master
│   │   ├── poleno-db-interface
│   │   └── poleno-ml
│   ├── models
│   │   ├── real1
│   │   │   ├── eval
│   │   │   │   ├── poleno-5_19022020-01112021.csv
│   │   │   │   └── poleno-5_19022020-20022020.csv
│   │   │   ├── model
│   │   │   │   ├── assets
│   │   │   │   ├── keras_metadata.pb
│   │   │   │   ├── model_info.json
│   │   │   │   ├── saved_model.pb
│   │   │   │   └── variables
│   │   │   │       ├── variables.data-00000-of-00001
│   │   │   │       └── variables.index
│   │   │   └── training
│   │   │       ├── checkpoints
│   │   │       ├── logs
│   │   │       ├── test_cache_new-pollens_other_spores_holo_aug.data-00000-of-00001
│   │   │       ├── test_cache_new-pollens_other_spores_holo_aug.index
│   │   │       ├── train_cache_new-pollens_other_spores_holo_aug.data-00000-of-00001
│   │   │       └── train_cache_new-pollens_other_spores_holo_aug.index
│   ├── training.ipynb
│   ├── validation.ipynb
│   └── validation_input
│       ├── hirst_pay_19022020-01112021.csv
│       └── hirst_pay_19022020-24052020.csv
├── tensorflow-tutorials
└── tmp
    ├── CharPyLS-master
    ├── poleno-db-interface
    └── poleno-ml
```
    
All files related to a model's training will be saved to `/tf/home/models/<model_name>/`. The cached training and validation sets, logs, and checkpoints are saved to `training/`. The trained model and its information file (`model_info.json`) are saved to `model/`. The model's predictions for a validation period are saved as CSV files to `eval/`.
  
## Ideas of things to try
  
- Try different image normalization (e.g. remove the mean pixel value).
- Try different data augmentation techniques, data preprocessing and filters.
- Train the models by swapping dataset collections in and out. Try different combinations.
- Train with an additional "trash" class.
- Train a binary neural network (or clustering algorithm) to replace filters which would separate "trash" from relevant particles.
- Try other ConvNet architectures.
- Instead of training 2 parallel networks (1 per holo image) and concat their results, try to stack the inputs to have a 3D input with 2 channels.
- Try the objectosphere loss.
- Explain the model with techniques such as [this one](https://towardsdatascience.com/understanding-your-convolution-network-with-visualizations-a4883441533b).

## Setup a new Docker environment

### Links

- https://www.tensorflow.org/install/docker?hl=fr
- https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html#setting-up-nvidia-container-toolkit
- ( https://phoenixnap.com/kb/install-docker-on-ubuntu-20-04 )
- https://docs.docker.com/config/daemon/systemd/#httphttps-proxy

### Install Docker
```
sudo apt update
sudo apt-get remove docker docker-engine docker.io
( sudo snap install docker )
sudo apt install docker.io
docker --version
```
If you do not want to use sudo each time:
https://docs.docker.com/engine/install/linux-postinstall/

### Setting up NVIDIA Container Toolkit
```
distribution=$(. /etc/os-release;echo $ID$VERSION_ID) \
      && curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
      && curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
            sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
            sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update
sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

### Proxy
```
sudo mkdir -p /etc/systemd/system/docker.service.d
sudo nano /etc/systemd/system/docker.service.d/http-proxy.conf
	and write the following lines:
		[Service]
		Environment="HTTP_PROXY=http://proxy.meteoswiss.ch:8080/"
		Environment="HTTPS_PROXY=http://proxy.meteoswiss.ch:8080/"
sudo systemctl daemon-reload
sudo systemctl show --property Environment docker
sudo systemctl restart docker
```
