#!/usr/bin/env bash
# Staged install matching the authors' pinned versions (CPU build). Run on Linux or WSL2 Ubuntu 22.04.
# These exact versions were verified to install and train on Linux x86_64, Python 3.9 (2026-11-09, pip + source builds).
# The conda + data.pyg.org wheel route below is checked per machine in story M1-01: fix versions here AND in environment.yml.
set -euo pipefail
conda create -n kairos python=3.9 -y
eval "$(conda shell.bash hook)"
conda activate kairos
pip install torch==1.13.1 torchvision==0.14.1 torchaudio==0.13.1 --index-url https://download.pytorch.org/whl/cpu
pip install "setuptools<70"  # newer setuptools breaks source builds of torch-scatter/torch-sparse
pip install torch-scatter==2.1.1 torch-sparse==0.6.17 torch-cluster==1.6.1 torch-spline-conv==1.2.2 \
    -f https://data.pyg.org/whl/torch-1.13.0+cpu.html
pip install torch-geometric==2.0.0
pip install "numpy<2" scikit-learn==1.2.0 scipy==1.11.1 networkx==2.8.7 pandas==2.0.3 \
    matplotlib tqdm psutil pytest
pip install -e .
python -c "import torch, torch_geometric; print('torch', torch.__version__, 'pyg', torch_geometric.__version__)"
