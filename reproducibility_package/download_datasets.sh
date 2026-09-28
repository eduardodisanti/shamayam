#!/usr/bin/env bash
set -e

echo "========================================="
echo " Downloading CWRU_Bearing_NumPy Dataset "
echo "========================================="
curl -L -o CWRU.zip https://github.com/srigas/CWRU_Bearing_NumPy/archive/refs/heads/master.zip
unzip -q CWRU.zip
rm CWRU.zip
echo "CWRU dataset successfully downloaded and extracted to CWRU_Bearing_NumPy-master"
echo ""

echo "========================================="
echo " Downloading NASA IMS Bearing Dataset   "
echo "========================================="
echo "Attempting direct download from NASA portal..."
# The legacy NASA URL might occasionally redirect or require updates.
# If this fails, users are instructed to download manually.
if curl -L -o IMS.zip https://data.nasa.gov/docs/legacy/IMS.zip; then
    unzip -q IMS.zip -d NASA_IMS
    rm IMS.zip
    echo "NASA IMS dataset successfully downloaded and extracted to NASA_IMS"
else
    echo "Direct download for NASA IMS failed."
    echo "Please download it manually from: https://data.nasa.gov/dataset/ims-bearings"
    echo "or from Kaggle: https://www.kaggle.com/datasets/vinayak123tyagi/bearing-dataset"
    echo "Extract it such that the '1st_test', '2nd_test', and '3rd_test' directories are accessible."
fi

echo ""
echo "Data download step complete."
