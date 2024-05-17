

To build the image, you can use the following command:

```bash
docker build -t aiidalab/qe-tar-home .
```

To run the container, you can use the following command:

```bash
docker run --rm -it -p 8888:8888 aiidalab/qe-tar-home
```

To compare with the image without the home directory, you can use the following command:

```bash
docker run --rm -it aiidalab/qe:amd64-latest /bin/bash
```




## Image size


5.21 GB, 12 s


6.4 GB, 12 s

