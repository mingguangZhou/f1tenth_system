#!/usr/bin/env bash

# create workspace on host, in home directory
mkdir -p $HOME/f1tenth_ws

# give docker permission to use X
sudo xhost +si:localuser:root

# Stop and remove any container with the same name
sudo docker rm -f f1tenth_onboard

sudo ln -sf /usr/lib/aarch64-linux-gnu/libffi.so.8.1.0 /usr/lib/aarch64-linux-gnu/libffi.so
sudo ln -sf /usr/lib/aarch64-linux-gnu/libffi.so.8.1.0 /usr/lib/aarch64-linux-gnu/libffi.so.8

# Start the container with a permanent name and make necessary fixes
sudo docker run --runtime nvidia -it --privileged --network host -e DISPLAY=$DISPLAY \
    -v /tmp/.X11-unix/:/tmp/.X11-unix -v /dev:/dev \
    --mount type=volume,dst=/f1tenth_ws,volume-driver=local,volume-opt=type=none,volume-opt=o=bind,volume-opt=device=$HOME/f1tenth_ws \
    --name f1tenth_onboard \
    f1tenth/focal-l4t-foxy:f1tenth-stack
