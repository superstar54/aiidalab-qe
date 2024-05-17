# check if /home is empty by checking if /home/.bashrc exists
if [ ! -f /home/.bashrc ]; then
  # check if /opt/home.tar.gz exists
  if [ -f /opt/home.tar.gz ]; then
    # untar /opt/home.tar.gz to /home
    tar -xzf /opt/home.tar.gz -C /home
    # remove /opt/home.tar.gz
    rm /opt/home.tar.gz
  fi
fi
