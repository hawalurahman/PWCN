# Use the Anaconda base image
FROM continuumio/anaconda3:2023.09-0

# Set the working directory
WORKDIR /app

# Copy your Conda environment YAML file into the container
COPY environment.yml .

# Create a Conda environment and activate it
RUN conda create --name myenv python=3.7

# Activate the Conda environment
SHELL ["conda", "run", "-n", "myenv", "/bin/bash", "-c"]

# Add any additional setup or configuration here
RUN conda install -y pytorch=1.4.0 spacy=2.3.5 numpy=1.19.2 scikit-learn

# Copy your application code into the container
COPY . /app

# Specify the command to run your application
CMD tail -f /dev/null
# CMD python train.py --model_name pwcn_dep --dataset restaurant
# docker build -t tes:v1 .
