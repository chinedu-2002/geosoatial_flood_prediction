{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": 2,
   "id": "fd1cc5ab-9810-4fc8-bc2f-cc11ac5a0ff6",
   "metadata": {},
   "outputs": [],
   "source": [
    "import os\n",
    "import pandas as pd\n",
    "import geopandas as gpd\n",
    "import xarray as xr\n",
    "import re\n",
    "import h5py\n",
    "from shapely import Point\n",
    "import rasterio\n",
    "import numpy as np\n",
    "import matplotlib.pyplot as plt\n",
    "import richdem as rd"
   ]
  },
  {
   "cell_type": "markdown",
   "id": "2a836803-3354-47b4-863f-d4d65b7ec9ad",
   "metadata": {},
   "source": [
    "# Handling Rainfall Dataset"
   ]
  },
  {
   "cell_type": "markdown",
   "id": "d45134e0-e143-4450-8a35-5c5927a17f05",
   "metadata": {},
   "source": [
    "### Convert rainfall .nc4 to .cvs.gz"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 13,
   "id": "16366f99-2f1c-4d0e-b439-039effeaf434",
   "metadata": {
    "scrolled": true
   },
   "outputs": [],
   "source": [
    "# Set input and output folders\n",
    "input_folder = \"datasets/Rainfall\"\n",
    "output_folder = \"gpm_csv_florida\""
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 125,
   "id": "bc792565-cc4f-474d-b357-5d2e09f22e60",
   "metadata": {
    "scrolled": true
   },
   "outputs": [],
   "source": [
    "\n",
    "os.makedirs(output_folder, exist_ok=True)\n",
    "\n",
    "# Florida bounding box\n",
    "lat_min, lat_max = 24.5, 31.0\n",
    "lon_min, lon_max = -87.7, -79.8\n",
    "\n",
    "# Regular expression to extract date\n",
    "date_pattern = re.compile(r\"(\\d{8})\")\n",
    "\n",
    "# Loop through all .nc4 files\n",
    "for filename in sorted(os.listdir(input_folder)):\n",
    "    if filename.endswith(\".nc4\"):\n",
    "        file_path = os.path.join(input_folder, filename)\n",
    "\n",
    "        # Extract date from filename\n",
    "        match = date_pattern.search(filename)\n",
    "        if not match:\n",
    "            print(f\"⚠️ Skipping (no date): {filename}\")\n",
    "            continue\n",
    "        date_str = match.group(1)\n",
    "        date_formatted = f\"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}\"\n",
    "        output_file = f\"gpm_rainfall_{date_formatted}.csv\"\n",
    "        output_path = os.path.join(output_folder, output_file)\n",
    "\n",
    "        try:\n",
    "            # Open dataset\n",
    "            ds = xr.open_dataset(file_path)\n",
    "\n",
    "            # Get precipitation variable (time=0)\n",
    "            if 'precipitation' in ds.variables:\n",
    "                rain = ds['precipitation'].isel(time=0)\n",
    "            elif 'precipitationCal' in ds.variables:\n",
    "                rain = ds['precipitationCal'].isel(time=0)\n",
    "            else:\n",
    "                raise KeyError(\"No precipitation variable found in this file.\")\n",
    "\n",
    "            # Crop to Florida bounding box\n",
    "            rain_fl = rain.sel(lat=slice(lat_min, lat_max), lon=slice(lon_min, lon_max))\n",
    "\n",
    "            # Convert to DataFrame\n",
    "            df = rain_fl.to_dataframe(name='rainfall').reset_index()\n",
    "            df['date'] = date_formatted\n",
    "\n",
    "            # Save to CSV\n",
    "            df.to_csv(output_path, index=False)\n",
    "            print(f\"\\r✔ Saved: {output_file}\\r\", end=\"\")\n",
    "\n",
    "            ds.close()\n",
    "\n",
    "        except Exception as e:\n",
    "            print(f\"❌ Error processing {filename}: {e}\")\n"
   ]
  },
  {
   "cell_type": "markdown",
   "id": "d45ab882-ec3f-49cf-9c05-00ee1356f06d",
   "metadata": {},
   "source": [
    "### concatenate to a single csv file"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 98,
   "id": "10b07347-9d82-4578-b4e7-d7afbf8735a8",
   "metadata": {},
   "outputs": [
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "✅ Done! All files concatenated to all_gpm_rainfall.csv\n"
     ]
    }
   ],
   "source": [
    "\n",
    "# Input folder\n",
    "input_folder = \"gpm_csv_florida\"\n",
    "\n",
    "# Output CSV\n",
    "output_file = \"all_gpm_rainfall.csv\"\n",
    "\n",
    "# Flag to control writing header once\n",
    "first_file = True\n",
    "\n",
    "for filename in sorted(os.listdir(input_folder)):\n",
    "    if filename.endswith(\".csv\") or filename.endswith(\".csv.gz\"):\n",
    "        file_path = os.path.join(input_folder, filename)\n",
    "        print(f\"\\rAppending: {filename}\\r\", end=\"\")\n",
    "        \n",
    "        # Stream load\n",
    "        for chunk in pd.read_csv(file_path, chunksize=100000):\n",
    "            chunk.to_csv(output_file, mode='a', index=False, header=first_file)\n",
    "            first_file = False\n",
    "\n",
    "print(f\"✅ Done! All files concatenated to {output_file}\")\n",
    "\n"
   ]
  },
  {
   "cell_type": "markdown",
   "id": "6f0928e0-9cea-4f2e-8ced-9a89290371ed",
   "metadata": {},
   "source": [
    "### Spatial join with county shape"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 102,
   "id": "163f850e-469e-47d0-bfbb-f4c75d36be86",
   "metadata": {},
   "outputs": [],
   "source": [
    "# rainfall = pd.read_csv(\"datasets/all_gpm_rainfall.csv\")\n",
    "counties = gpd.read_file(\"datasets/county_shape/tl_2024_us_county.shp\").to_crs(\"EPSG:4326\")\n",
    "florida = counties[counties[\"STATEFP\"] == \"12\"]\n",
    "florida = florida[[\"GEOID\", \"geometry\"]]\n",
    "\n",
    "rainfall = gpd.GeoDataFrame(rainfall, \n",
    "                            geometry=gpd.points_from_xy(rainfall[\"longitude\"], rainfall[\"latitude\"]),\n",
    "                            crs=\"EPSG:4326\")\n",
    "rainfall_counties = rainfall.sjoin(florida, how=\"inner\", predicate=\"intersects\")\n"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 104,
   "id": "a2fd5e95-5bec-4220-8667-d8519c89f068",
   "metadata": {},
   "outputs": [],
   "source": [
    "rainfall_counties.to_csv(\"datasets/rainfall_counties.csv.gz\", index=False, compression=\"gzip\")"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 107,
   "id": "1dfafeb4-c870-47ee-a5b9-173ae872a395",
   "metadata": {},
   "outputs": [
    {
     "data": {
      "text/plain": [
       "<Axes: >"
      ]
     },
     "execution_count": 107,
     "metadata": {},
     "output_type": "execute_result"
    },
    {
     "data": {
      "image/png": "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AIBUaGpqktfrDXu7dWf4bW9vV319vcaOHasjR45kzFl+/X6/SkpKqDnJqDk1qDk1sr1mY4yampo0YsSIXs+6bF2PKicnR5dccokkqaCgIGNevE7UnBrUnBrUnBrZXHNvPalOTKYAAFiNoAIAWM3KoPJ4PHrwwQfl8XjSXUrEqDk1qDk1qDk1qDky1k2mAACgKyt7VAAAdCKoAABWI6gAAFYjqAAAVrMuqA4dOqS5c+dq8ODBKigo0JQpU/Tqq68GbbNr1y5de+21uvjiizVo0CCVl5dr79696SlYfdf81FNPyXGckJfjx49bWXOnp556SuPHj9eAAQM0bNgwLV68OA3VnhdJzaGe4yeeeCJNFUf+PEvSxx9/rOLiYjmOoz/96U+pLbSLvmr++OOPNXv2bI0YMUIej0clJSVavHhxWtfn7KvmN998U7fddptKSkqUl5enMWPG6PHHH09bvVJk741vfetbmjhxojwejyZMmJCeQruIpOb3339fN954oy688EINHjxY3/zmN3Xu3Lm47te6oJozZ45aW1v1yiuvaM+ePZowYYK+9KUvqbGxUdL5NaFmzZqlz372s/rd736n7du3q6CgQLNmzdKnn35qZc3z589XQ0ND0GXWrFmaPn26ioqKrKxZkh577DHdf//9+t73vqf9+/fr5Zdf1qxZs9JSb6Q1S9KqVauCnuvbb789TRVHXrMk3XHHHRo/fnwaqgzWV805OTmaO3euNm3apEOHDumpp57SSy+9pG984xvW1rxnzx4NGTJETz/9tPbv36/7779fy5Yt009/+lNra5bOLzG0cOFCzZ8/P211dtVXzW1tbZozZ46am5u1fft2rVu3Ts8++6z+8R//Mb47NhY5ceKEkWS2bdsWuM7v9xtJ5qWXXjLGGLNr1y4jybz//vuBbd566y0jyfzxj3+0subujh8/bvr162dWr16dqjKDRFLzyZMnTV5eXtjHkGqRPs+SzPr169NQYU/RvDd+9rOfmenTp5uXX37ZSDKnTp1KcbXnxfJ+NsaYxx9/3BQXF6eixB5irfnuu+82M2bMSEWJPURb84MPPmg+//nPp7DCniKp+fnnnzc5OTnmww8/DGyzdu1a4/F4jM/ni/m+repRfeYzn9GYMWO0evVqNTc3q7W1VT//+c81dOhQTZw4UZI0evRoDR48WCtXrtS5c+d09uxZ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",
      "text/plain": [
       "<Figure size 640x480 with 1 Axes>"
      ]
     },
     "metadata": {},
     "output_type": "display_data"
    }
   ],
   "source": [
    "ax = florida.plot(edgecolor=\"black\", facecolor='none')\n",
    "rainfall_counties.plot(ax=ax, color=\"red\")"
   ]
  },
  {
   "cell_type": "markdown",
   "id": "32caf9c5-8524-4cf9-aba2-9a3b4a233346",
   "metadata": {
    "jp-MarkdownHeadingCollapsed": true
   },
   "source": [
    "# Handling Soil Moisture Dataset"
   ]
  },
  {
   "cell_type": "markdown",
   "id": "b780620c-0c51-47ba-8009-5f329c137117",
   "metadata": {
    "jp-MarkdownHeadingCollapsed": true
   },
   "source": [
    "### Converting to csv"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 139,
   "id": "57f79b83-c30a-44f0-83f5-9b1c2e65529c",
   "metadata": {},
   "outputs": [
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "✔ Saved: smap_florida_2025-01-01.csv.gz"
     ]
    }
   ],
   "source": [
    "# Root paths\n",
    "input_root    = \"datasets/smap\"\n",
    "output_folder = \"datasets/soil_moisture\"\n",
    "os.makedirs(output_folder, exist_ok=True)\n",
    "\n",
    "# Florida bounding box\n",
    "lat_min, lat_max = 24.5, 31.0\n",
    "lon_min, lon_max = -87.7, -79.8\n",
    "\n",
    "# Columns to keep\n",
    "cols = ['latitude', 'longitude', 'soil_moisture']\n",
    "\n",
    "# Regex for date\n",
    "date_pattern = re.compile(r\"_([0-9]{8})_\")\n",
    "\n",
    "# Loop through .h5 files directly in root\n",
    "for filename in sorted(os.listdir(input_root)):\n",
    "    if not filename.endswith(\".h5\"):\n",
    "        continue\n",
    "\n",
    "    match = date_pattern.search(filename)\n",
    "    if not match:\n",
    "        print(f\"⚠️ Skipping (no date): {filename}\")\n",
    "        continue\n",
    "\n",
    "    date_str       = match.group(1)\n",
    "    date_formatted = f\"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}\"\n",
    "    output_filename = f\"smap_florida_{date_formatted}.csv.gz\"\n",
    "    output_path     = os.path.join(output_folder, output_filename)\n",
    "    file_path       = os.path.join(input_root, filename)\n",
    "\n",
    "    try:\n",
    "        with h5py.File(file_path, \"r\") as f:\n",
    "            group = f[\"Soil_Moisture_Retrieval_Data_AM\"]\n",
    "\n",
    "            data = {}\n",
    "            for var_name, dset in group.items():\n",
    "                if isinstance(dset, h5py.Dataset):\n",
    "                    data[var_name] = dset[()].flatten()\n",
    "\n",
    "            df = pd.DataFrame(data)\n",
    "            df = df[cols]\n",
    "            df = df[df['soil_moisture'] > -9999]\n",
    "\n",
    "            # ✅ Crop to Florida\n",
    "            df = df[\n",
    "                (df['latitude'].between(lat_min, lat_max)) &\n",
    "                (df['longitude'].between(lon_min, lon_max))\n",
    "            ]\n",
    "            df['date'] = date_formatted\n",
    "\n",
    "        # ✅ Save as compressed CSV\n",
    "        df.to_csv(output_path, index=False, compression=\"gzip\")\n",
    "        print(f\"\\r✔ Saved: {output_filename}\\r\", end=\"\")\n",
    "\n",
    "    except Exception as e:\n",
    "        print(f\"❌ Error processing {filename}: {e}\")\n"
   ]
  },
  {
   "cell_type": "markdown",
   "id": "8d98f1da-d2a2-4113-8fcc-e272ed274832",
   "metadata": {},
   "source": [
    "### Concatenating into one tabular data"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 9,
   "id": "8c17060c-36a5-4472-8e0e-2b34d62b63a1",
   "metadata": {
    "scrolled": true
   },
   "outputs": [
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "Merged All file successfully01.csv.gz...\n"
     ]
    }
   ],
   "source": [
    "input_folder = \"datasets/soil_moisture\"\n",
    "output_file = \"datasets/all_soil_moisture.csv.gz\"\n",
    "first_file = True\n",
    "\n",
    "for filename in sorted(os.listdir(input_folder)):\n",
    "    if filename.endswith(\".csv.gz\"):\n",
    "        \n",
    "        filepath = os.path.join(input_folder, filename)\n",
    "        print(f\"\\rAdding {filename}...\\r\", end=\"\")\n",
    "\n",
    "        try:\n",
    "            for chunck in pd.read_csv(filepath, chunksize=100000):\n",
    "                chunck.to_csv(output_file, mode='a', index=False, compression=\"gzip\", header=first_file)\n",
    "                first_file = False\n",
    "        except Exception as e:\n",
    "            print(f\"Error Processing {filename}: {e}\")\n",
    "\n",
    "print(\"Merged All file successfully\")\n",
    "                          "
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 12,
   "id": "439ac2b3-df78-441c-88e8-75b624ef0cd9",
   "metadata": {},
   "outputs": [
    {
     "data": {
      "text/html": [
       "<div>\n",
       "<style scoped>\n",
       "    .dataframe tbody tr th:only-of-type {\n",
       "        vertical-align: middle;\n",
       "    }\n",
       "\n",
       "    .dataframe tbody tr th {\n",
       "        vertical-align: top;\n",
       "    }\n",
       "\n",
       "    .dataframe thead th {\n",
       "        text-align: right;\n",
       "    }\n",
       "</style>\n",
       "<table border=\"1\" class=\"dataframe\">\n",
       "  <thead>\n",
       "    <tr style=\"text-align: right;\">\n",
       "      <th></th>\n",
       "      <th>latitude</th>\n",
       "      <th>longitude</th>\n",
       "      <th>soil_moisture</th>\n",
       "      <th>date</th>\n",
       "    </tr>\n",
       "  </thead>\n",
       "  <tbody>\n",
       "    <tr>\n",
       "      <th>0</th>\n",
       "      <td>30.925072</td>\n",
       "      <td>-85.005190</td>\n",
       "      <td>0.179516</td>\n",
       "      <td>2015-04-01</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>1</th>\n",
       "      <td>30.925072</td>\n",
       "      <td>-84.911830</td>\n",
       "      <td>0.191564</td>\n",
       "      <td>2015-04-01</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>2</th>\n",
       "      <td>30.925072</td>\n",
       "      <td>-84.818470</td>\n",
       "      <td>0.207285</td>\n",
       "      <td>2015-04-01</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>3</th>\n",
       "      <td>30.925072</td>\n",
       "      <td>-84.725105</td>\n",
       "      <td>0.172415</td>\n",
       "      <td>2015-04-01</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>4</th>\n",
       "      <td>30.925072</td>\n",
       "      <td>-84.631744</td>\n",
       "      <td>0.176616</td>\n",
       "      <td>2015-04-01</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>...</th>\n",
       "      <td>...</td>\n",
       "      <td>...</td>\n",
       "      <td>...</td>\n",
       "      <td>...</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>2708099</th>\n",
       "      <td>25.256830</td>\n",
       "      <td>-80.897300</td>\n",
       "      <td>0.411062</td>\n",
       "      <td>2025-01-01</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>2708100</th>\n",
       "      <td>25.256830</td>\n",
       "      <td>-80.803940</td>\n",
       "      <td>0.442439</td>\n",
       "      <td>2025-01-01</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>2708101</th>\n",
       "      <td>25.256830</td>\n",
       "      <td>-80.710580</td>\n",
       "      <td>0.469371</td>\n",
       "      <td>2025-01-01</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>2708102</th>\n",
       "      <td>25.256830</td>\n",
       "      <td>-80.617220</td>\n",
       "      <td>0.412335</td>\n",
       "      <td>2025-01-01</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>2708103</th>\n",
       "      <td>25.256830</td>\n",
       "      <td>-80.523860</td>\n",
       "      <td>0.349341</td>\n",
       "      <td>2025-01-01</td>\n",
       "    </tr>\n",
       "  </tbody>\n",
       "</table>\n",
       "<p>2708104 rows × 4 columns</p>\n",
       "</div>"
      ],
      "text/plain": [
       "          latitude  longitude  soil_moisture        date\n",
       "0        30.925072 -85.005190       0.179516  2015-04-01\n",
       "1        30.925072 -84.911830       0.191564  2015-04-01\n",
       "2        30.925072 -84.818470       0.207285  2015-04-01\n",
       "3        30.925072 -84.725105       0.172415  2015-04-01\n",
       "4        30.925072 -84.631744       0.176616  2015-04-01\n",
       "...            ...        ...            ...         ...\n",
       "2708099  25.256830 -80.897300       0.411062  2025-01-01\n",
       "2708100  25.256830 -80.803940       0.442439  2025-01-01\n",
       "2708101  25.256830 -80.710580       0.469371  2025-01-01\n",
       "2708102  25.256830 -80.617220       0.412335  2025-01-01\n",
       "2708103  25.256830 -80.523860       0.349341  2025-01-01\n",
       "\n",
       "[2708104 rows x 4 columns]"
      ]
     },
     "execution_count": 12,
     "metadata": {},
     "output_type": "execute_result"
    }
   ],
   "source": []
  },
  {
   "cell_type": "markdown",
   "id": "d7d253cd-b760-481b-b29d-5ee0d8fb667a",
   "metadata": {},
   "source": [
    "### Spatial join with counties GEOID"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 108,
   "id": "56e60ad7-ab24-4216-85b1-528bcf7a2555",
   "metadata": {},
   "outputs": [],
   "source": [
    "counties = gpd.read_file(\"datasets/county_shape/tl_2024_us_county.shp\").to_crs(\"EPSG:4326\")\n",
    "soil_moisture = pd.read_csv(\"datasets/all_soil_moisture.csv.gz\")\n",
    "\n",
    "florida = counties[counties[\"STATEFP\"] == \"12\"]\n",
    "\n",
    "florida = florida[[\"GEOID\", \"geometry\"]]\n"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 109,
   "id": "d1f90605-7413-4f1f-b1ea-a1993731146a",
   "metadata": {},
   "outputs": [],
   "source": [
    "soil_moisture = gpd.GeoDataFrame(soil_moisture, \n",
    "                                 geometry=gpd.points_from_xy(soil_moisture[\"longitude\"], soil_moisture[\"latitude\"]),\n",
    "                                 crs=\"EPSG:4326\")"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 110,
   "id": "b7892b7c-a008-47ed-a04f-817f153e4a42",
   "metadata": {},
   "outputs": [],
   "source": [
    "soil_moisture = soil_moisture.drop(columns=[\"latitude\", \"longitude\"])"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 84,
   "id": "81e938a5-fe74-4d73-91bc-aed22bd767ae",
   "metadata": {},
   "outputs": [
    {
     "data": {
      "text/html": [
       "<div>\n",
       "<style scoped>\n",
       "    .dataframe tbody tr th:only-of-type {\n",
       "        vertical-align: middle;\n",
       "    }\n",
       "\n",
       "    .dataframe tbody tr th {\n",
       "        vertical-align: top;\n",
       "    }\n",
       "\n",
       "    .dataframe thead th {\n",
       "        text-align: right;\n",
       "    }\n",
       "</style>\n",
       "<table border=\"1\" class=\"dataframe\">\n",
       "  <thead>\n",
       "    <tr style=\"text-align: right;\">\n",
       "      <th></th>\n",
       "      <th>soil_moisture</th>\n",
       "      <th>date</th>\n",
       "      <th>geometry</th>\n",
       "    </tr>\n",
       "  </thead>\n",
       "  <tbody>\n",
       "    <tr>\n",
       "      <th>0</th>\n",
       "      <td>0.179516</td>\n",
       "      <td>2015-04-01</td>\n",
       "      <td>POINT (-85.00519 30.92507)</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>1</th>\n",
       "      <td>0.191564</td>\n",
       "      <td>2015-04-01</td>\n",
       "      <td>POINT (-84.91183 30.92507)</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>2</th>\n",
       "      <td>0.207285</td>\n",
       "      <td>2015-04-01</td>\n",
       "      <td>POINT (-84.81847 30.92507)</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>3</th>\n",
       "      <td>0.172415</td>\n",
       "      <td>2015-04-01</td>\n",
       "      <td>POINT (-84.7251 30.92507)</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>4</th>\n",
       "      <td>0.176616</td>\n",
       "      <td>2015-04-01</td>\n",
       "      <td>POINT (-84.63174 30.92507)</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>...</th>\n",
       "      <td>...</td>\n",
       "      <td>...</td>\n",
       "      <td>...</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>2708099</th>\n",
       "      <td>0.411062</td>\n",
       "      <td>2025-01-01</td>\n",
       "      <td>POINT (-80.8973 25.25683)</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>2708100</th>\n",
       "      <td>0.442439</td>\n",
       "      <td>2025-01-01</td>\n",
       "      <td>POINT (-80.80394 25.25683)</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>2708101</th>\n",
       "      <td>0.469371</td>\n",
       "      <td>2025-01-01</td>\n",
       "      <td>POINT (-80.71058 25.25683)</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>2708102</th>\n",
       "      <td>0.412335</td>\n",
       "      <td>2025-01-01</td>\n",
       "      <td>POINT (-80.61722 25.25683)</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>2708103</th>\n",
       "      <td>0.349341</td>\n",
       "      <td>2025-01-01</td>\n",
       "      <td>POINT (-80.52386 25.25683)</td>\n",
       "    </tr>\n",
       "  </tbody>\n",
       "</table>\n",
       "<p>2708104 rows × 3 columns</p>\n",
       "</div>"
      ],
      "text/plain": [
       "         soil_moisture        date                    geometry\n",
       "0             0.179516  2015-04-01  POINT (-85.00519 30.92507)\n",
       "1             0.191564  2015-04-01  POINT (-84.91183 30.92507)\n",
       "2             0.207285  2015-04-01  POINT (-84.81847 30.92507)\n",
       "3             0.172415  2015-04-01   POINT (-84.7251 30.92507)\n",
       "4             0.176616  2015-04-01  POINT (-84.63174 30.92507)\n",
       "...                ...         ...                         ...\n",
       "2708099       0.411062  2025-01-01   POINT (-80.8973 25.25683)\n",
       "2708100       0.442439  2025-01-01  POINT (-80.80394 25.25683)\n",
       "2708101       0.469371  2025-01-01  POINT (-80.71058 25.25683)\n",
       "2708102       0.412335  2025-01-01  POINT (-80.61722 25.25683)\n",
       "2708103       0.349341  2025-01-01  POINT (-80.52386 25.25683)\n",
       "\n",
       "[2708104 rows x 3 columns]"
      ]
     },
     "execution_count": 84,
     "metadata": {},
     "output_type": "execute_result"
    }
   ],
   "source": [
    "soil_moisture"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 111,
   "id": "a8bea6ff-50b8-4b61-995b-4d232fffa4a6",
   "metadata": {},
   "outputs": [],
   "source": [
    "soil_moisture_counties = soil_moisture.sjoin(florida, how=\"inner\", predicate=\"intersects\")"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 112,
   "id": "70f3e1d6-00e8-4e2f-beee-e0a19d8ef700",
   "metadata": {},
   "outputs": [],
   "source": [
    "n = soil_moisture_counties[soil_moisture_counties[\"GEOID\"].isna()]"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 113,
   "id": "f4f7a85a-9133-44bc-b5d0-9ff79949f82e",
   "metadata": {},
   "outputs": [
    {
     "data": {
      "text/html": [
       "<div>\n",
       "<style scoped>\n",
       "    .dataframe tbody tr th:only-of-type {\n",
       "        vertical-align: middle;\n",
       "    }\n",
       "\n",
       "    .dataframe tbody tr th {\n",
       "        vertical-align: top;\n",
       "    }\n",
       "\n",
       "    .dataframe thead th {\n",
       "        text-align: right;\n",
       "    }\n",
       "</style>\n",
       "<table border=\"1\" class=\"dataframe\">\n",
       "  <thead>\n",
       "    <tr style=\"text-align: right;\">\n",
       "      <th></th>\n",
       "      <th>soil_moisture</th>\n",
       "      <th>date</th>\n",
       "      <th>geometry</th>\n",
       "      <th>index_right</th>\n",
       "      <th>GEOID</th>\n",
       "    </tr>\n",
       "  </thead>\n",
       "  <tbody>\n",
       "    <tr>\n",
       "      <th>0</th>\n",
       "      <td>0.179516</td>\n",
       "      <td>2015-04-01</td>\n",
       "      <td>POINT (-85.00519 30.92507)</td>\n",
       "      <td>2580</td>\n",
       "      <td>12063</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>38</th>\n",
       "      <td>0.194009</td>\n",
       "      <td>2015-04-01</td>\n",
       "      <td>POINT (-85.00519 30.84308)</td>\n",
       "      <td>2580</td>\n",
       "      <td>12063</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>76</th>\n",
       "      <td>0.236677</td>\n",
       "      <td>2015-04-01</td>\n",
       "      <td>POINT (-85.00519 30.76117)</td>\n",
       "      <td>2580</td>\n",
       "      <td>12063</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>109</th>\n",
       "      <td>0.395620</td>\n",
       "      <td>2015-04-01</td>\n",
       "      <td>POINT (-81.92427 30.76117)</td>\n",
       "      <td>2687</td>\n",
       "      <td>12089</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>110</th>\n",
       "      <td>0.435699</td>\n",
       "      <td>2015-04-01</td>\n",
       "      <td>POINT (-81.83091 30.76117)</td>\n",
       "      <td>2687</td>\n",
       "      <td>12089</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>...</th>\n",
       "      <td>...</td>\n",
       "      <td>...</td>\n",
       "      <td>...</td>\n",
       "      <td>...</td>\n",
       "      <td>...</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>2708099</th>\n",
       "      <td>0.411062</td>\n",
       "      <td>2025-01-01</td>\n",
       "      <td>POINT (-80.8973 25.25683)</td>\n",
       "      <td>1390</td>\n",
       "      <td>12087</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>2708100</th>\n",
       "      <td>0.442439</td>\n",
       "      <td>2025-01-01</td>\n",
       "      <td>POINT (-80.80394 25.25683)</td>\n",
       "      <td>369</td>\n",
       "      <td>12086</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>2708101</th>\n",
       "      <td>0.469371</td>\n",
       "      <td>2025-01-01</td>\n",
       "      <td>POINT (-80.71058 25.25683)</td>\n",
       "      <td>369</td>\n",
       "      <td>12086</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>2708102</th>\n",
       "      <td>0.412335</td>\n",
       "      <td>2025-01-01</td>\n",
       "      <td>POINT (-80.61722 25.25683)</td>\n",
       "      <td>369</td>\n",
       "      <td>12086</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>2708103</th>\n",
       "      <td>0.349341</td>\n",
       "      <td>2025-01-01</td>\n",
       "      <td>POINT (-80.52386 25.25683)</td>\n",
       "      <td>369</td>\n",
       "      <td>12086</td>\n",
       "    </tr>\n",
       "  </tbody>\n",
       "</table>\n",
       "<p>2469812 rows × 5 columns</p>\n",
       "</div>"
      ],
      "text/plain": [
       "         soil_moisture        date                    geometry  index_right  \\\n",
       "0             0.179516  2015-04-01  POINT (-85.00519 30.92507)         2580   \n",
       "38            0.194009  2015-04-01  POINT (-85.00519 30.84308)         2580   \n",
       "76            0.236677  2015-04-01  POINT (-85.00519 30.76117)         2580   \n",
       "109           0.395620  2015-04-01  POINT (-81.92427 30.76117)         2687   \n",
       "110           0.435699  2015-04-01  POINT (-81.83091 30.76117)         2687   \n",
       "...                ...         ...                         ...          ...   \n",
       "2708099       0.411062  2025-01-01   POINT (-80.8973 25.25683)         1390   \n",
       "2708100       0.442439  2025-01-01  POINT (-80.80394 25.25683)          369   \n",
       "2708101       0.469371  2025-01-01  POINT (-80.71058 25.25683)          369   \n",
       "2708102       0.412335  2025-01-01  POINT (-80.61722 25.25683)          369   \n",
       "2708103       0.349341  2025-01-01  POINT (-80.52386 25.25683)          369   \n",
       "\n",
       "         GEOID  \n",
       "0        12063  \n",
       "38       12063  \n",
       "76       12063  \n",
       "109      12089  \n",
       "110      12089  \n",
       "...        ...  \n",
       "2708099  12087  \n",
       "2708100  12086  \n",
       "2708101  12086  \n",
       "2708102  12086  \n",
       "2708103  12086  \n",
       "\n",
       "[2469812 rows x 5 columns]"
      ]
     },
     "execution_count": 113,
     "metadata": {},
     "output_type": "execute_result"
    }
   ],
   "source": [
    "soil_moisture_counties"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 88,
   "id": "3ee03920-bdef-438a-aeee-5fce042bb97c",
   "metadata": {},
   "outputs": [
    {
     "data": {
      "text/plain": [
       "<Axes: >"
      ]
     },
     "execution_count": 88,
     "metadata": {},
     "output_type": "execute_result"
    },
    {
     "data": {
      "image/png": "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",
      "text/plain": [
       "<Figure size 640x480 with 1 Axes>"
      ]
     },
     "metadata": {},
     "output_type": "display_data"
    }
   ],
   "source": [
    "ax = florida.plot(edgecolor='black', facecolor='none')\n",
    "soil_moisture.plot(ax=ax, color='red')"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 114,
   "id": "90ae712c-6d21-4d65-8e1d-2a56b16bfc94",
   "metadata": {},
   "outputs": [],
   "source": [
    "soil_moisture_counties.to_csv(\"datasets/soil_moisture_counties.csv.gz\", index=False, compression=\"gzip\")\n",
    "    "
   ]
  },
  {
   "cell_type": "markdown",
   "id": "5c4de96f-438b-4106-9a10-3e50e101b156",
   "metadata": {
    "jp-MarkdownHeadingCollapsed": true
   },
   "source": [
    "# Handling NASADEM"
   ]
  },
  {
   "cell_type": "markdown",
   "id": "3e660d45-00c7-4684-bb10-cf7458202f3e",
   "metadata": {},
   "source": [
    "### Merge elevation tiffs"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 80,
   "id": "af61c83b-680f-46d3-ba63-eae2145b326a",
   "metadata": {},
   "outputs": [
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "0...10...20...30...40...50...60...70...80...90...100 - done.\n"
     ]
    }
   ],
   "source": [
    "!gdal_merge.py -o merged_output.tif -n -9999 -a_nodata -9999 datasets/NASADEM/output_be.tif datasets/NASADEM/output_be_2.tif\n"
   ]
  },
  {
   "cell_type": "markdown",
   "id": "e3734286-c4fb-43d8-af99-e0290552ada8",
   "metadata": {},
   "source": [
    "### Merge Slope tiffs"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 84,
   "id": "53cb9892-044a-49d6-a689-4e6aecfc1a10",
   "metadata": {},
   "outputs": [
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "0...10...20...30...40...50...60...70...80...90...100 - done.\n"
     ]
    }
   ],
   "source": [
    "!gdal_merge.py -o merged_slope_output.tif -n -9999 -a_nodata -9999 datasets/NASADEM/viz.be_slope.tif datasets/NASADEM/viz.be_slope2.tif\n"
   ]
  },
  {
   "cell_type": "markdown",
   "id": "7baf0f28-1830-428e-a052-d4733445488a",
   "metadata": {},
   "source": [
    "### Using rainfall coordinates to get elevation"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 130,
   "id": "1c93fe1f-cdd9-4eee-9778-a3aa22dfaa39",
   "metadata": {},
   "outputs": [],
   "source": [
    "elevation_df = (pd.read_csv(\"datasets/joined_counties/rainfall_counties.csv.gz\")\n",
    "            .query('time < \"2015-01-02\"')\n",
    "            .loc[:,['GEOID', 'longitude', 'latitude']]\n",
    "           )\n",
    "\n",
    "with rasterio.open(\"datasets/NASADEM/merged_elevation.tif\") as src2:\n",
    "    elevation = src2.read(1)\n",
    "    transform = src2.transform\n",
    "    elevation_df[\"elevation\"] = elevation_df.apply(\n",
    "        lambda row: get_elevation(elevation, transform, row['longitude'], row['latitude']),\n",
    "        axis=1\n",
    "    )"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 131,
   "id": "a06166b2-a88a-4a70-be6d-a9bd974f2769",
   "metadata": {},
   "outputs": [],
   "source": [
    "el = elevation_df"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 132,
   "id": "f3988a24-cbe5-4e5c-aae1-fb3c4792e44e",
   "metadata": {},
   "outputs": [
    {
     "data": {
      "text/html": [
       "<div>\n",
       "<style scoped>\n",
       "    .dataframe tbody tr th:only-of-type {\n",
       "        vertical-align: middle;\n",
       "    }\n",
       "\n",
       "    .dataframe tbody tr th {\n",
       "        vertical-align: top;\n",
       "    }\n",
       "\n",
       "    .dataframe thead th {\n",
       "        text-align: right;\n",
       "    }\n",
       "</style>\n",
       "<table border=\"1\" class=\"dataframe\">\n",
       "  <thead>\n",
       "    <tr style=\"text-align: right;\">\n",
       "      <th></th>\n",
       "      <th>GEOID</th>\n",
       "      <th>longitude</th>\n",
       "      <th>latitude</th>\n",
       "      <th>elevation</th>\n",
       "    </tr>\n",
       "  </thead>\n",
       "  <tbody>\n",
       "    <tr>\n",
       "      <th>0</th>\n",
       "      <td>12033</td>\n",
       "      <td>-87.55</td>\n",
       "      <td>30.85</td>\n",
       "      <td>48</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>1</th>\n",
       "      <td>12033</td>\n",
       "      <td>-87.55</td>\n",
       "      <td>30.95</td>\n",
       "      <td>78</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>2</th>\n",
       "      <td>12033</td>\n",
       "      <td>-87.45</td>\n",
       "      <td>30.15</td>\n",
       "      <td>0</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>3</th>\n",
       "      <td>12033</td>\n",
       "      <td>-87.45</td>\n",
       "      <td>30.25</td>\n",
       "      <td>0</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>4</th>\n",
       "      <td>12033</td>\n",
       "      <td>-87.45</td>\n",
       "      <td>30.35</td>\n",
       "      <td>0</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>...</th>\n",
       "      <td>...</td>\n",
       "      <td>...</td>\n",
       "      <td>...</td>\n",
       "      <td>...</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>1694</th>\n",
       "      <td>12099</td>\n",
       "      <td>-80.05</td>\n",
       "      <td>26.65</td>\n",
       "      <td>6</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>1695</th>\n",
       "      <td>12099</td>\n",
       "      <td>-80.05</td>\n",
       "      <td>26.75</td>\n",
       "      <td>1</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>1696</th>\n",
       "      <td>12099</td>\n",
       "      <td>-80.05</td>\n",
       "      <td>26.85</td>\n",
       "      <td>8</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>1697</th>\n",
       "      <td>12099</td>\n",
       "      <td>-80.05</td>\n",
       "      <td>26.95</td>\n",
       "      <td>0</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>1698</th>\n",
       "      <td>12085</td>\n",
       "      <td>-80.05</td>\n",
       "      <td>27.05</td>\n",
       "      <td>0</td>\n",
       "    </tr>\n",
       "  </tbody>\n",
       "</table>\n",
       "<p>1699 rows × 4 columns</p>\n",
       "</div>"
      ],
      "text/plain": [
       "      GEOID  longitude  latitude  elevation\n",
       "0     12033     -87.55     30.85         48\n",
       "1     12033     -87.55     30.95         78\n",
       "2     12033     -87.45     30.15          0\n",
       "3     12033     -87.45     30.25          0\n",
       "4     12033     -87.45     30.35          0\n",
       "...     ...        ...       ...        ...\n",
       "1694  12099     -80.05     26.65          6\n",
       "1695  12099     -80.05     26.75          1\n",
       "1696  12099     -80.05     26.85          8\n",
       "1697  12099     -80.05     26.95          0\n",
       "1698  12085     -80.05     27.05          0\n",
       "\n",
       "[1699 rows x 4 columns]"
      ]
     },
     "execution_count": 132,
     "metadata": {},
     "output_type": "execute_result"
    }
   ],
   "source": [
    "el"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 133,
   "id": "402190a0-979a-45c4-8b11-430a05ff619c",
   "metadata": {},
   "outputs": [],
   "source": [
    "el = el[(el['elevation'] >=-50) & (el['elevation'] <=100)]\n",
    "\n"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 134,
   "id": "d0642474-d78b-40bf-be20-efb04d0ae22b",
   "metadata": {},
   "outputs": [
    {
     "data": {
      "image/png": "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",
      "text/plain": [
       "<Figure size 640x480 with 1 Axes>"
      ]
     },
     "metadata": {},
     "output_type": "display_data"
    }
   ],
   "source": [
    "fig, ax = plt.subplots()\n",
    "ax.hist(el['elevation'], bins=100)\n",
    "plt.show()"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 135,
   "id": "a6d17f6f-6829-4f7c-9a4a-b7066a33d98e",
   "metadata": {},
   "outputs": [],
   "source": [
    "final_elevation_counties = el.groupby('GEOID')['elevation'].agg(['min', 'max', 'mean', 'std'])\n",
    "\n",
    "final_elevation_counties = final_elevation_counties.reset_index()\n",
    "final_elevation_counties = final_elevation_counties.rename(columns={'min': 'elev_min',\n",
    "                                                            'max': 'elev_max',\n",
    "                                                            'mean': 'elev_mean',\n",
    "                                                            'std': 'elev_std'\n",
    "    \n",
    "})\n",
    "\n",
    "final_elevation_counties.to_csv(\"datasets/joined_counties/final_elevation_counties.csv\", index=False)\n"
   ]
  },
  {
   "cell_type": "markdown",
   "id": "0fcb9829-f9c7-4a47-90cc-6017022d2c21",
   "metadata": {},
   "source": [
    "### Handle slope"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 105,
   "id": "d41c07da-f080-4399-8247-8f105a5fe86f",
   "metadata": {},
   "outputs": [],
   "source": [
    "slope_df = (pd.read_csv(\"datasets/joined_counties/rainfall_counties.csv.gz\")\n",
    "            .query('time < \"2015-01-02\"')\n",
    "            .loc[:,['GEOID', 'longitude', 'latitude']]\n",
    "           )\n",
    "\n",
    "with rasterio.open(\"datasets/NASADEM/merged_slope.tif\") as src:\n",
    "    slope = src.read(1)\n",
    "    transform = src.transform\n",
    "    slope_df[\"slope\"] = slope_df.apply(\n",
    "        lambda row: get_elevation(slope, transform, row['longitude'], row['latitude']),\n",
    "        axis=1\n",
    "    )"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 106,
   "id": "c6330883-eb0b-4e9b-ad4b-530e66637f56",
   "metadata": {},
   "outputs": [],
   "source": [
    "slope_df.to_csv(\"datasets/joined_counties/final_slope_counties.csv\", index=False)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 118,
   "id": "6a91541f-9b5c-46bc-8f4a-5a7104954602",
   "metadata": {},
   "outputs": [],
   "source": [
    "slope_df = slope_df[slope_df['slope'] > -9999]"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 119,
   "id": "b11b8329-ac66-4e04-9169-32d1a0e60df6",
   "metadata": {},
   "outputs": [
    {
     "data": {
      "image/png": "iVBORw0KGgoAAAANSUhEUgAAAigAAAGdCAYAAAA44ojeAAAAOXRFWHRTb2Z0d2FyZQBNYXRwbG90bGliIHZlcnNpb24zLjkuMiwgaHR0cHM6Ly9tYXRwbG90bGliLm9yZy8hTgPZAAAACXBIWXMAAA9hAAAPYQGoP6dpAAAor0lEQVR4nO3df3BU133//9dGPxZQpC1CSKstQlYdwIMlM4lwAfkHvwWqAdswBYcOhYZ4cAy0imBswNOxvp0EYVyD01ITJ0MQP+yISUGOZyAYMYAcopACgRqwS0gtYlG0Vk3FroTllQzn80e+7GSFJFixQmdXz8fMmeHe+75nz5njHb18995dhzHGCAAAwCJf6e0BAAAAtEdAAQAA1iGgAAAA6xBQAACAdQgoAADAOgQUAABgHQIKAACwDgEFAABYJ763B9AdN27c0OXLl5WcnCyHw9HbwwEAAHfAGKOmpiZ5PB595StdXyOJyoBy+fJlZWVl9fYwAABAN9TV1WnIkCFd1kRlQElOTpb0xwmmpKT08mgAAMCd8Pv9ysrKCv4d70pUBpSbH+ukpKQQUAAAiDJ3cnsGN8kCAADrEFAAAIB1CCgAAMA6BBQAAGAdAgoAALAOAQUAAFiHgAIAAKxDQAEAANYhoAAAAOsQUAAAgHUIKAAAwDoEFAAAYB0CCgAAsA4BBQAAWCe+twdgo/tW7Q3ZvrjuiV4aCQAAfRNXUAAAgHUIKAAAwDoEFAAAYB0CCgAAsA4BBQAAWIeAAgAArENAAQAA1iGgAAAA6xBQAACAdQgoAADAOgQUAABgHQIKAACwDgEFAABYh4ACAACsQ0ABAADWIaAAAADrEFAAAIB1CCgAAMA6YQWUzZs366GHHlJKSopSUlI0btw4/eIXvwgeX7RokRwOR0gbO3ZsSB+BQEDLly9XWlqakpKSNGvWLF26dCkyswEAADEhrIAyZMgQrVu3TidOnNCJEyc0adIkPfnkkzp37lywZvr06aqvrw+2ffv2hfRRXFysyspKVVRU6OjRo2pubtaMGTN0/fr1yMwIAABEvfhwimfOnBmy/f3vf1+bN2/WsWPH9OCDD0qSnE6n3G53h+f7fD5t2bJFO3bs0JQpUyRJO3fuVFZWlg4ePKhp06Z1Zw4AACDGdPselOvXr6uiokLXrl3TuHHjgvuPHDmi9PR0DR8+XM8++6waGhqCx06ePKm2tjYVFhYG93k8HuXm5qqmpqbT1woEAvL7/SENAADErrADypkzZ/TVr35VTqdTzz33nCorKzVy5EhJUlFRkd566y0dOnRIr732mo4fP65JkyYpEAhIkrxerxITEzVw4MCQPjMyMuT1ejt9zbKyMrlcrmDLysoKd9gAACCKhPURjySNGDFCp0+f1tWrV7V7924tXLhQ1dXVGjlypObNmxesy83N1ejRo5Wdna29e/dq9uzZnfZpjJHD4ej0+OrVq1VSUhLc9vv9hBQAAGJY2AElMTFRX/va1yRJo0eP1vHjx/WDH/xAb7755i21mZmZys7O1oULFyRJbrdbra2tamxsDLmK0tDQoIKCgk5f0+l0yul0hjtUAAAQpe76e1CMMcGPcNq7cuWK6urqlJmZKUnKz89XQkKCqqqqgjX19fU6e/ZslwEFAAD0LWFdQVmzZo2KioqUlZWlpqYmVVRU6MiRI9q/f7+am5tVWlqqOXPmKDMzUxcvXtSaNWuUlpamp59+WpLkcrm0ePFirVixQoMGDVJqaqpWrlypvLy84FM9AAAAYQWUTz/9VAsWLFB9fb1cLpceeugh7d+/X1OnTlVLS4vOnDmj7du36+rVq8rMzNTEiRO1a9cuJScnB/vYuHGj4uPjNXfuXLW0tGjy5MkqLy9XXFxcxCcHAACik8MYY3p7EOHy+/1yuVzy+XxKSUmJeP/3rdobsn1x3RMRfw0AAPqacP5+81s8AADAOgQUAABgHQIKAACwDgEFAABYh4ACAACsQ0ABAADWIaAAAADrEFAAAIB1CCgAAMA6BBQAAGAdAgoAALAOAQUAAFiHgAIAAKxDQAEAANYhoAAAAOsQUAAAgHUIKAAAwDoEFAAAYB0CCgAAsA4BBQAAWIeAAgAArENAAQAA1iGgAAAA6xBQAACAdQgoAADAOgQUAABgHQIKAACwDgEFAABYh4ACAACsQ0ABAADWIaAAAADrEFAAAIB1CCgAAMA6BBQAAGAdAgoAALAOAQUAAFgnrICyefNmPfTQQ0pJSVFKSorGjRunX/ziF8HjxhiVlpbK4/Gof//+mjBhgs6dOxfSRyAQ0PLly5WWlqakpCTNmjVLly5disxsAABATAgroAwZMkTr1q3TiRMndOLECU2aNElPPvlkMISsX79eGzZs0KZNm3T8+HG53W5NnTpVTU1NwT6Ki4tVWVmpiooKHT16VM3NzZoxY4auX78e2ZkBAICo5TDGmLvpIDU1Va+++qq+9a1vyePxqLi4WC+++KKkP14tycjI0CuvvKIlS5bI5/Np8ODB2rFjh+bNmydJunz5srKysrRv3z5Nmzbtjl7T7/fL5XLJ5/MpJSXlbobfoftW7Q3ZvrjuiYi/BgAAfU04f7+7fQ/K9evXVVFRoWvXrmncuHGqra2V1+tVYWFhsMbpdGr8+PGqqamRJJ08eVJtbW0hNR6PR7m5ucGajgQCAfn9/pAGAABiV9gB5cyZM/rqV78qp9Op5557TpWVlRo5cqS8Xq8kKSMjI6Q+IyMjeMzr9SoxMVEDBw7stKYjZWVlcrlcwZaVlRXusAEAQBQJO6CMGDFCp0+f1rFjx/Sd73xHCxcu1Icffhg87nA4QuqNMbfsa+92NatXr5bP5wu2urq6cIcNAACiSNgBJTExUV/72tc0evRolZWVadSoUfrBD34gt9stSbdcCWloaAheVXG73WptbVVjY2OnNR1xOp3BJ4duNgAAELvu+ntQjDEKBALKycmR2+1WVVVV8Fhra6uqq6tVUFAgScrPz1dCQkJITX19vc6ePRusAQAAiA+neM2aNSoqKlJWVpaamppUUVGhI0eOaP/+/XI4HCouLtbatWs1bNgwDRs2TGvXrtWAAQM0f/58SZLL5dLixYu1YsUKDRo0SKmpqVq5cqXy8vI0ZcqUHpkgAACIPmEFlE8//VQLFixQfX29XC6XHnroIe3fv19Tp06VJL3wwgtqaWnR888/r8bGRo0ZM0YHDhxQcnJysI+NGzcqPj5ec+fOVUtLiyZPnqzy8nLFxcVFdmYAACBq3fX3oPQGvgcFAIDoc0++BwUAAKCnEFAAAIB1CCgAAMA6BBQAAGAdAgoAALAOAQUAAFiHgAIAAKxDQAEAANYhoAAAAOsQUAAAgHUIKAAAwDoEFAAAYB0CCgAAsA4BBQAAWIeAAgAArENAAQAA1iGgAAAA6xBQAACAdQgoAADAOgQUAABgHQIKAACwDgEFAABYh4ACAACsQ0ABAADWIaAAAADrEFAAAIB1CCgAAMA6BBQAAGAdAgoAALAOAQUAAFiHgAIAAKxDQAEAANYhoAAAAOsQUAAAgHUIKAAAwDoEFAAAYJ2wAkpZWZkefvhhJScnKz09XU899ZTOnz8fUrNo0SI5HI6QNnbs2JCaQCCg5cuXKy0tTUlJSZo1a5YuXbp097MBAAAxIayAUl1draVLl+rYsWOqqqrSl19+qcLCQl27di2kbvr06aqvrw+2ffv2hRwvLi5WZWWlKioqdPToUTU3N2vGjBm6fv363c8IAABEvfhwivfv3x+yvXXrVqWnp+vkyZN6/PHHg/udTqfcbneHffh8Pm3ZskU7duzQlClTJEk7d+5UVlaWDh48qGnTpoU7BwAAEGPu6h4Un88nSUpNTQ3Zf+TIEaWnp2v48OF69tln1dDQEDx28uRJtbW1qbCwMLjP4/EoNzdXNTU1Hb5OIBCQ3+8PaQAAIHZ1O6AYY1RSUqJHH31Uubm5wf1FRUV66623dOjQIb322ms6fvy4Jk2apEAgIEnyer1KTEzUwIEDQ/rLyMiQ1+vt8LXKysrkcrmCLSsrq7vDBgAAUSCsj3j+1LJly/TBBx/o6NGjIfvnzZsX/Hdubq5Gjx6t7Oxs7d27V7Nnz+60P2OMHA5Hh8dWr16tkpKS4Lbf7yekAAAQw7p1BWX58uV69913dfjwYQ0ZMqTL2szMTGVnZ+vChQuSJLfbrdbWVjU2NobUNTQ0KCMjo8M+nE6nUlJSQhoAAIhdYQUUY4yWLVumPXv26NChQ8rJybntOVeuXFFdXZ0yMzMlSfn5+UpISFBVVVWwpr6+XmfPnlVBQUGYwwcAALEorI94li5dqrfffls///nPlZycHLxnxOVyqX///mpublZpaanmzJmjzMxMXbx4UWvWrFFaWpqefvrpYO3ixYu1YsUKDRo0SKmpqVq5cqXy8vKCT/UAAIC+LayAsnnzZknShAkTQvZv3bpVixYtUlxcnM6cOaPt27fr6tWryszM1MSJE7Vr1y4lJycH6zdu3Kj4+HjNnTtXLS0tmjx5ssrLyxUXF3f3MwIAAFHPYYwxvT2IcPn9frlcLvl8vh65H+W+VXtDti+ueyLirwEAQF8Tzt9vfosHAABYh4ACAACsQ0ABAADWIaAAAADrEFAAAIB1CCgAAMA6BBQAAGAdAgoAALAOAQUAAFiHgAIAAKxDQAEAANYhoAAAAOsQUAAAgHUIKAAAwDoEFAAAYB0CCgAAsA4BBQAAWIeAAgAArENAAQAA1iGgAAAA6xBQAACAdQgoAADAOgQUAABgHQIKAACwDgEFAABYh4ACAACsQ0ABAADWIaAAAADrEFAAAIB1CCgAAMA6BBQAAGAdAgoAALAOAQUAAFiHgAIAAKxDQAEAANYhoAAAAOuEFVDKysr08MMPKzk5Wenp6Xrqqad0/vz5kBpjjEpLS+XxeNS/f39NmDBB586dC6kJBAJavny50tLSlJSUpFmzZunSpUt3PxsAABATwgoo1dXVWrp0qY4dO6aqqip9+eWXKiws1LVr14I169ev14YNG7Rp0yYdP35cbrdbU6dOVVNTU7CmuLhYlZWVqqio0NGjR9Xc3KwZM2bo+vXrkZsZAACIWg5jjOnuyf/7v/+r9PR0VVdX6/HHH5cxRh6PR8XFxXrxxRcl/fFqSUZGhl555RUtWbJEPp9PgwcP1o4dOzRv3jxJ0uXLl5WVlaV9+/Zp2rRpt31dv98vl8sln8+nlJSU7g6/U/et2huyfXHdExF/DQAA+ppw/n7f1T0oPp9PkpSamipJqq2tldfrVWFhYbDG6XRq/PjxqqmpkSSdPHlSbW1tITUej0e5ubnBmvYCgYD8fn9IAwAAsavbAcUYo5KSEj366KPKzc2VJHm9XklSRkZGSG1GRkbwmNfrVWJiogYOHNhpTXtlZWVyuVzBlpWV1d1hAwCAKNDtgLJs2TJ98MEH+ulPf3rLMYfDEbJtjLllX3td1axevVo+ny/Y6urqujtsAAAQBboVUJYvX653331Xhw8f1pAhQ4L73W63JN1yJaShoSF4VcXtdqu1tVWNjY2d1rTndDqVkpIS0gAAQOwKK6AYY7Rs2TLt2bNHhw4dUk5OTsjxnJwcud1uVVVVBfe1traqurpaBQUFkqT8/HwlJCSE1NTX1+vs2bPBGgAA0LfFh1O8dOlSvf322/r5z3+u5OTk4JUSl8ul/v37y+FwqLi4WGvXrtWwYcM0bNgwrV27VgMGDND8+fODtYsXL9aKFSs0aNAgpaamauXKlcrLy9OUKVMiP0MAABB1wgoomzdvliRNmDAhZP/WrVu1aNEiSdILL7yglpYWPf/882psbNSYMWN04MABJScnB+s3btyo+Ph4zZ07Vy0tLZo8ebLKy8sVFxd3d7MBAAAx4a6+B6W38D0oAABEn3v2PSgAAAA9gYACAACsQ0ABAADWIaAAAADrEFAAAIB1CCgAAMA6BBQAAGAdAgoAALAOAQUAAFiHgAIAAKxDQAEAANYhoAAAAOsQUAAAgHUIKAAAwDoEFAAAYB0CCgAAsA4BBQAAWIeAAgAArENAAQAA1iGgAAAA6xBQAACAdQgoAADAOgQUAABgHQIKAACwDgEFAABYh4ACAACsQ0ABAADWIaAAAADrEFAAAIB1CCgAAMA6BBQAAGAdAgoAALAOAQUAAFiHgAIAAKxDQAEAANYhoAAAAOuEHVDef/99zZw5Ux6PRw6HQ++8807I8UWLFsnhcIS0sWPHhtQEAgEtX75caWlpSkpK0qxZs3Tp0qW7mggAAIgdYQeUa9euadSoUdq0aVOnNdOnT1d9fX2w7du3L+R4cXGxKisrVVFRoaNHj6q5uVkzZszQ9evXw58BAACIOfHhnlBUVKSioqIua5xOp9xud4fHfD6ftmzZoh07dmjKlCmSpJ07dyorK0sHDx7UtGnTwh0SAACIMT1yD8qRI0eUnp6u4cOH69lnn1VDQ0Pw2MmTJ9XW1qbCwsLgPo/Ho9zcXNXU1HTYXyAQkN/vD2kAACB2RTygFBUV6a233tKhQ4f02muv6fjx45o0aZICgYAkyev1KjExUQMHDgw5LyMjQ16vt8M+y8rK5HK5gi0rKyvSwwYAABYJ+yOe25k3b17w37m5uRo9erSys7O1d+9ezZ49u9PzjDFyOBwdHlu9erVKSkqC236/n5ACAEAM6/HHjDMzM5Wdna0LFy5Iktxut1pbW9XY2BhS19DQoIyMjA77cDqdSklJCWkAACB29XhAuXLliurq6pSZmSlJys/PV0JCgqqqqoI19fX1Onv2rAoKCnp6OAAAIAqE/RFPc3Ozfv/73we3a2trdfr0aaWmpio1NVWlpaWaM2eOMjMzdfHiRa1Zs0ZpaWl6+umnJUkul0uLFy/WihUrNGjQIKWmpmrlypXKy8sLPtUDAAD6trADyokTJzRx4sTg9s17QxYuXKjNmzfrzJkz2r59u65evarMzExNnDhRu3btUnJycvCcjRs3Kj4+XnPnzlVLS4smT56s8vJyxcXFRWBKAAAg2jmMMaa3BxEuv98vl8sln8/XI/ej3Ldqb8j2xXVPRPw1AADoa8L5+81v8QAAAOsQUAAAgHUIKAAAwDoEFAAAYB0CCgAAsA4BBQAAWIeAAgAArENAAQAA1iGgAAAA6xBQAACAdQgoAADAOgQUAABgHQIKAACwDgEFAABYh4ACAACsQ0ABAADWIaAAAADrEFAAAIB1CCgAAMA6BBQAAGAdAgoAALAOAQUAAFiHgAIAAKxDQAEAANYhoAAAAOsQUAAAgHUIKAAAwDoEFAAAYB0CCgAAsA4BBQAAWIeAAgAArENAAQAA1iGgAAAA6xBQAACAdQgoAADAOgQUAABgnbADyvvvv6+ZM2fK4/HI4XDonXfeCTlujFFpaak8Ho/69++vCRMm6Ny5cyE1gUBAy5cvV1pampKSkjRr1ixdunTpriYCAABiR9gB5dq1axo1apQ2bdrU4fH169drw4YN2rRpk44fPy63262pU6eqqakpWFNcXKzKykpVVFTo6NGjam5u1owZM3T9+vXuzwQAAMSM+HBPKCoqUlFRUYfHjDF6/fXX9dJLL2n27NmSpG3btikjI0Nvv/22lixZIp/Ppy1btmjHjh2aMmWKJGnnzp3KysrSwYMHNW3atLuYDgAAiAURvQeltrZWXq9XhYWFwX1Op1Pjx49XTU2NJOnkyZNqa2sLqfF4PMrNzQ3WtBcIBOT3+0MaAACIXRENKF6vV5KUkZERsj8jIyN4zOv1KjExUQMHDuy0pr2ysjK5XK5gy8rKiuSwAQCAZXrkKR6HwxGybYy5ZV97XdWsXr1aPp8v2Orq6iI2VgAAYJ+IBhS32y1Jt1wJaWhoCF5Vcbvdam1tVWNjY6c17TmdTqWkpIQ0AAAQuyIaUHJycuR2u1VVVRXc19raqurqahUUFEiS8vPzlZCQEFJTX1+vs2fPBmsAAEDfFvZTPM3Nzfr9738f3K6trdXp06eVmpqqoUOHqri4WGvXrtWwYcM0bNgwrV27VgMGDND8+fMlSS6XS4sXL9aKFSs0aNAgpaamauXKlcrLyws+1QMAAPq2sAPKiRMnNHHixOB2SUmJJGnhwoUqLy/XCy+8oJaWFj3//PNqbGzUmDFjdODAASUnJwfP2bhxo+Lj4zV37ly1tLRo8uTJKi8vV1xcXASmBAAAop3DGGN6exDh8vv9crlc8vl8PXI/yn2r9oZsX1z3RMRfAwCAviacv9/8Fg8AALAOAQUAAFgn7HtQ0LPaf7wk8RETAKDv4QoKAACwDgEFAABYh4ACAACsQ0ABAADWIaAAAADrEFAAAIB1CCgAAMA6BBQAAGAdAgoAALAOAQUAAFiHgAIAAKxDQAEAANbhxwKjQPsfEOTHAwEAsY4rKAAAwDoEFAAAYB0CCgAAsA4BBQAAWIebZPuQ9jfbStxwCwCwE1dQAACAdQgoAADAOgQUAABgHQIKAACwDjfJxqiObogFACBacAUFAABYhysoERIrj/DGyjwAANGNKygAAMA6BBQAAGAdAgoAALAO96DcQ9zfAQDAneEKCgAAsA4BBQAAWIeAAgAArENAAQAA1ol4QCktLZXD4Qhpbrc7eNwYo9LSUnk8HvXv318TJkzQuXPnIj0MAAAQxXrkKZ4HH3xQBw8eDG7HxcUF/71+/Xpt2LBB5eXlGj58uL73ve9p6tSpOn/+vJKTk3tiOFbjN3MAALhVjwSU+Pj4kKsmNxlj9Prrr+ull17S7NmzJUnbtm1TRkaG3n77bS1ZsqQnhtMnEHQAALGkR+5BuXDhgjwej3JycvTMM8/o448/liTV1tbK6/WqsLAwWOt0OjV+/HjV1NR02l8gEJDf7w9pAAAgdkU8oIwZM0bbt2/Xe++9px//+Mfyer0qKCjQlStX5PV6JUkZGRkh52RkZASPdaSsrEwulyvYsrKyIj1sAABgkYgHlKKiIs2ZM0d5eXmaMmWK9u7940cP27ZtC9Y4HI6Qc4wxt+z7U6tXr5bP5wu2urq6SA8bAABYpMcfM05KSlJeXp4uXLgQvC+l/dWShoaGW66q/Cmn06mUlJSQBgAAYlePB5RAIKCPPvpImZmZysnJkdvtVlVVVfB4a2urqqurVVBQ0NNDAQAAUSLiT/GsXLlSM2fO1NChQ9XQ0KDvfe978vv9WrhwoRwOh4qLi7V27VoNGzZMw4YN09q1azVgwADNnz8/0kMBAABRKuIB5dKlS/rmN7+pzz77TIMHD9bYsWN17NgxZWdnS5JeeOEFtbS06Pnnn1djY6PGjBmjAwcO9MnvQLHBvXw8uf1r8UvOAIDORDygVFRUdHnc4XCotLRUpaWlkX5pAAAQI3rki9rQ93B1BAAQSQQUhI1vrQUA9DQCShQiIAAAYl2PP2YMAAAQLgIKAACwDgEFAABYh3tQehD3igAA0D1cQQEAANbhCgpuiytBAIB7jSsoAADAOlxB6SauKgAA0HO4ggIAAKzDFZQ7wNUSAADuLQIKek1HwY8fGQQASAQU9BCuOgEA7gb3oAAAAOtwBQVWaX/lhY98AKBv4goKAACwDgEFAABYh4ACAACswz0osBqPIgNA30RAQZ9wJ0GHMAQA9iCgIOoRLAAg9nAPCgAAsA4BBQAAWIePeNBn8XX8AGAvAgqiDsECAGIfH/EAAADrEFAAAIB1+IgH6MKd/Hhhb/7AIY9YA4hVBBTgHuBXmgEgPHzEAwAArENAAQAA1iGgAAAA63APChBhfE8LANw9AgpiUk+FBMJH13iqCECk9GpAeeONN/Tqq6+qvr5eDz74oF5//XU99thjvTkkIOp1J0R1N0QQ2AD0lF4LKLt27VJxcbHeeOMNPfLII3rzzTdVVFSkDz/8UEOHDu2tYQH3xJ1cabiXVyO6O57u9N3b3yXDI99AdOi1gLJhwwYtXrxY3/72tyVJr7/+ut577z1t3rxZZWVlvTUsoNfcSQDoK1cs7mSedxIsIhWq7uT1IxXyCEzoDTZ+PNsrAaW1tVUnT57UqlWrQvYXFhaqpqbmlvpAIKBAIBDc9vl8kiS/398j47sR+LxH+gWiydDv/qxH+u3ofdud91ykxtfdfu7kvPZzvZN53km/Z/+/abetuVO5L78Xkb7b99OR9n13dE4k53a717oT93I8d/JakVqv9jr6b7Mn/sbe7NMYc/ti0wv+53/+x0gyv/rVr0L2f//73zfDhw+/pf7ll182kmg0Go1Go8VAq6uru21W6NWbZB0OR8i2MeaWfZK0evVqlZSUBLdv3Lih//u//9OgQYM6rL8bfr9fWVlZqqurU0pKSkT7thHzjW3MN7Yx39gWi/M1xqipqUkej+e2tb0SUNLS0hQXFyev1xuyv6GhQRkZGbfUO51OOZ3OkH1/9md/1pNDVEpKSsz8B3EnmG9sY76xjfnGtlibr8vluqO6Xvkm2cTEROXn56uqqipkf1VVlQoKCnpjSAAAwCK99hFPSUmJFixYoNGjR2vcuHH60Y9+pE8++UTPPfdcbw0JAABYotcCyrx583TlyhX90z/9k+rr65Wbm6t9+/YpOzu7t4Yk6Y8fJ7388su3fKQUq5hvbGO+sY35xra+Nt/2HMbcybM+AAAA9w6/ZgwAAKxDQAEAANYhoAAAAOsQUAAAgHX6ZEB54403lJOTo379+ik/P1+//OUvu6yvrq5Wfn6++vXrp7/4i7/QD3/4w3s00rtTVlamhx9+WMnJyUpPT9dTTz2l8+fPd3nOkSNH5HA4bmn/9V//dY9G3X2lpaW3jNvtdnd5TrSurSTdd999Ha7V0qVLO6yPtrV9//33NXPmTHk8HjkcDr3zzjshx40xKi0tlcfjUf/+/TVhwgSdO3futv3u3r1bI0eOlNPp1MiRI1VZWdlDMwhPV/Nta2vTiy++qLy8PCUlJcnj8ehv//Zvdfny5S77LC8v73DNv/jiix6eze3dbn0XLVp0y7jHjh17236jcX0ldbhODodDr776aqd92ry+kdDnAsquXbtUXFysl156SadOndJjjz2moqIiffLJJx3W19bW6q/+6q/02GOP6dSpU1qzZo3+/u//Xrt3777HIw9fdXW1li5dqmPHjqmqqkpffvmlCgsLde3atduee/78edXX1wfbsGHD7sGI796DDz4YMu4zZ850WhvNaytJx48fD5nrzS8+/Ou//usuz4uWtb127ZpGjRqlTZs2dXh8/fr12rBhgzZt2qTjx4/L7XZr6tSpampq6rTPX//615o3b54WLFig//zP/9SCBQs0d+5c/eY3v+mpadyxrub7+eef67e//a3+8R//Ub/97W+1Z88e/e53v9OsWbNu229KSkrIetfX16tfv349MYWw3G59JWn69Okh4963b1+XfUbr+kq6ZY1+8pOfyOFwaM6cOV32a+v6RkQkfvwvmvzlX/6lee6550L2PfDAA2bVqlUd1r/wwgvmgQceCNm3ZMkSM3bs2B4bY09paGgwkkx1dXWnNYcPHzaSTGNj470bWIS8/PLLZtSoUXdcH0tra4wx//AP/2Duv/9+c+PGjQ6PR/PaSjKVlZXB7Rs3bhi3223WrVsX3PfFF18Yl8tlfvjDH3baz9y5c8306dND9k2bNs0888wzER/z3Wg/3478x3/8h5Fk/vCHP3Ras3XrVuNyuSI7uB7Q0XwXLlxonnzyybD6iaX1ffLJJ82kSZO6rImW9e2uPnUFpbW1VSdPnlRhYWHI/sLCQtXU1HR4zq9//etb6qdNm6YTJ06ora2tx8baE3w+nyQpNTX1trVf//rXlZmZqcmTJ+vw4cM9PbSIuXDhgjwej3JycvTMM8/o448/7rQ2lta2tbVVO3fu1Le+9a3b/oBmtK7tn6qtrZXX6w1ZP6fTqfHjx3f6XpY6X/OuzrGVz+eTw+G47e+SNTc3Kzs7W0OGDNGMGTN06tSpezPACDhy5IjS09M1fPhwPfvss2poaOiyPlbW99NPP9XevXu1ePHi29ZG8/reTp8KKJ999pmuX79+yw8SZmRk3PLDhTd5vd4O67/88kt99tlnPTbWSDPGqKSkRI8++qhyc3M7rcvMzNSPfvQj7d69W3v27NGIESM0efJkvf/++/dwtN0zZswYbd++Xe+9955+/OMfy+v1qqCgQFeuXOmwPlbWVpLeeecdXb16VYsWLeq0JprXtr2b79dw3ss3zwv3HBt98cUXWrVqlebPn9/lj8g98MADKi8v17vvvquf/vSn6tevnx555BFduHDhHo62e4qKivTWW2/p0KFDeu2113T8+HFNmjRJgUCg03NiZX23bdum5ORkzZ49u8u6aF7fO9FrX3Xfm9r/H6Yxpsv/6+yovqP9Nlu2bJk++OADHT16tMu6ESNGaMSIEcHtcePGqa6uTv/8z/+sxx9/vKeHeVeKioqC/87Ly9O4ceN0//33a9u2bSopKenwnFhYW0nasmWLioqKuvwJ82he286E+17u7jk2aWtr0zPPPKMbN27ojTfe6LJ27NixITeWPvLII/rGN76hf/3Xf9W//Mu/9PRQ78q8efOC/87NzdXo0aOVnZ2tvXv3dvmHO9rXV5J+8pOf6G/+5m9uey9JNK/vnehTV1DS0tIUFxd3S5puaGi4JXXf5Ha7O6yPj4/XoEGDemyskbR8+XK9++67Onz4sIYMGRL2+WPHjo3KRJ6UlKS8vLxOxx4LaytJf/jDH3Tw4EF9+9vfDvvcaF3bm09nhfNevnleuOfYpK2tTXPnzlVtba2qqqq6vHrSka985St6+OGHo3LNMzMzlZ2d3eXYo319JemXv/ylzp8/3633czSvb0f6VEBJTExUfn5+8GmHm6qqqlRQUNDhOePGjbul/sCBAxo9erQSEhJ6bKyRYIzRsmXLtGfPHh06dEg5OTnd6ufUqVPKzMyM8Oh6XiAQ0EcffdTp2KN5bf/U1q1blZ6erieeeCLsc6N1bXNycuR2u0PWr7W1VdXV1Z2+l6XO17yrc2xxM5xcuHBBBw8e7FaINsbo9OnTUbnmV65cUV1dXZdjj+b1vWnLli3Kz8/XqFGjwj43mte3Q711d25vqaioMAkJCWbLli3mww8/NMXFxSYpKclcvHjRGGPMqlWrzIIFC4L1H3/8sRkwYID57ne/az788EOzZcsWk5CQYP793/+9t6Zwx77zne8Yl8tljhw5Yurr64Pt888/D9a0n+/GjRtNZWWl+d3vfmfOnj1rVq1aZSSZ3bt398YUwrJixQpz5MgR8/HHH5tjx46ZGTNmmOTk5Jhc25uuX79uhg4dal588cVbjkX72jY1NZlTp06ZU6dOGUlmw4YN5tSpU8GnVtatW2dcLpfZs2ePOXPmjPnmN79pMjMzjd/vD/axYMGCkCf0fvWrX5m4uDizbt0689FHH5l169aZ+Ph4c+zYsXs+v/a6mm9bW5uZNWuWGTJkiDl9+nTI+zkQCAT7aD/f0tJSs3//fvPf//3f5tSpU+bv/u7vTHx8vPnNb37TG1MM0dV8m5qazIoVK0xNTY2pra01hw8fNuPGjTN//ud/HpPre5PP5zMDBgwwmzdv7rCPaFrfSOhzAcUYY/7t3/7NZGdnm8TERPONb3wj5LHbhQsXmvHjx4fUHzlyxHz96183iYmJ5r777uv0Px7bSOqwbd26NVjTfr6vvPKKuf/++02/fv3MwIEDzaOPPmr27t177wffDfPmzTOZmZkmISHBeDweM3v2bHPu3Lng8Vha25vee+89I8mcP3/+lmPRvrY3H4tu3xYuXGiM+eOjxi+//LJxu93G6XSaxx9/3Jw5cyakj/Hjxwfrb/rZz35mRowYYRISEswDDzxgTUDrar61tbWdvp8PHz4c7KP9fIuLi83QoUNNYmKiGTx4sCksLDQ1NTX3fnId6Gq+n3/+uSksLDSDBw82CQkJZujQoWbhwoXmk08+CekjVtb3pjfffNP079/fXL16tcM+oml9I8FhzP9/VyAAAIAl+tQ9KAAAIDoQUAAAgHUIKAAAwDoEFAAAYB0CCgAAsA4BBQAAWIeAAgAArENAAQAA1iGgAAAA6xBQAACAdQgoAADAOgQUAABgnf8Hz4vj90MJZWkAAAAASUVORK5CYII=",
      "text/plain": [
       "<Figure size 640x480 with 1 Axes>"
      ]
     },
     "metadata": {},
     "output_type": "display_data"
    }
   ],
   "source": [
    "fig, ax = plt.subplots()\n",
    "ax.hist(slope_df['slope'], bins=100)\n",
    "plt.show()\n"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 136,
   "id": "dd75bf38-1dfc-40e8-b9b3-8110c85edac1",
   "metadata": {},
   "outputs": [],
   "source": [
    "final_slope = slope_df.groupby('GEOID')['slope'].agg(['min', 'max', 'mean', 'std'])"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 137,
   "id": "3fe97c21-a0eb-4863-a81a-2700cd810efd",
   "metadata": {
    "scrolled": true
   },
   "outputs": [],
   "source": [
    "final_slope = final_slope.rename(columns={'min': 'slope_min',\n",
    "                                                            'max': 'slope_max',\n",
    "                                                            'mean': 'slope_mean',\n",
    "                                                            'std': 'slope_std'\n",
    "                                                                   })\n",
    "\n",
    "final_slope  = final_slope .reset_index()\n",
    "\n",
    "\n",
    "final_slope .to_csv(\"datasets/joined_counties/final_slope_counties.csv\", index=False)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "42250728-7724-470d-a528-908d43fa6a87",
   "metadata": {},
   "outputs": [],
   "source": []
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "26970884-9a43-4cbe-bd66-a2860670fb7c",
   "metadata": {},
   "outputs": [],
   "source": []
  },
  {
   "cell_type": "code",
   "execution_count": 93,
   "id": "a73e25d8-6b48-448e-8115-b4f38bf26d86",
   "metadata": {
    "scrolled": true
   },
   "outputs": [],
   "source": [
    "def get_elevation(elevation, transform, lon, lat):\n",
    "    col = (lon - transform.c) / transform.a\n",
    "    row = (transform.f - lat) / (-transform.e)\n",
    "    \n",
    "    col = int(round(col))\n",
    "    row = int(round(row))\n",
    "\n",
    "    if 0 <= row < elevation.shape[0] and 0 <= col < elevation.shape[1]:\n",
    "        return elevation[row, col]\n",
    "    else:\n",
    "        return np.nan\n",
    "    "
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "ce737b10-ed79-4151-9dd0-ca9f5a167b84",
   "metadata": {},
   "outputs": [],
   "source": [
    "elevation_counties = elevation_counties[(elevation_counties['elevation'] >=-50) & (elevation_counties['elevation'] <=100)]\n",
    "\n",
    "elevation_counties['elevation'].describe()\n",
    "\n",
    "fig, ax = plt.subplots()\n",
    "ax.hist(elevation_counties[\"elevation\"], bins=100, range=(-10, 100))\n",
    "plt.show()\n",
    "\n",
    "final_elevation_counties = elevation_counties.groupby('GEOID')['elevation'].agg(['min', 'max', 'mean', 'std'])\n",
    "\n",
    "final_elevation_counties = final_elevation_counties.rename(columns={'min': 'elev_min',\n",
    "                                                            'max': 'elev_max',\n",
    "                                                            'mean': 'elev_mean',\n",
    "                                                            'std': 'elev_std'\n",
    "    \n",
    "})\n",
    "\n",
    "final_elevation_counties = final_elevation_counties.reset_index()\n",
    "\n",
    "final_elevation_counties\n",
    "\n",
    "final_elevation_counties.to_csv(\"datasets/joined_counties/final_elevation_counties.csv\", index=False)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "c28df7e9-a774-4f4f-82ce-2f72eee7b987",
   "metadata": {},
   "outputs": [],
   "source": []
  },
  {
   "cell_type": "code",
   "execution_count": 52,
   "id": "aee5d94e-4a5f-4785-805d-6b780e31f306",
   "metadata": {},
   "outputs": [],
   "source": [
    "def get_elevation(elevation, transform, lon, lat):\n",
    "    col = (lon - transform.c) / transform.a\n",
    "    row = (transform.f - lat) / (-transform.e)\n",
    "    \n",
    "    col = int(round(col))\n",
    "    row = int(round(row))\n",
    "\n",
    "    if 0 <= row < elevation.shape[0] and 0 <= col < elevation.shape[1]:\n",
    "        return elevation[row, col]\n",
    "    else:\n",
    "        return np.nan\n",
    "    "
   ]
  },
  {
   "cell_type": "markdown",
   "id": "a29bb7fc-857e-42c9-9cce-079d2dd3f9ed",
   "metadata": {},
   "source": [
    "# Handle Flood events"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 300,
   "id": "f5a989d5-3974-4ab9-83a5-d32fcccca6e1",
   "metadata": {},
   "outputs": [],
   "source": [
    "import pandas as pd\n",
    "\n",
    "def load_and_filter_storm_events(path):\n",
    "    \"\"\"\n",
    "    Loads storm event data, filters for Florida (STATE_FIPS == 12),\n",
    "    selects relevant columns, standardizes EVENT_TYPE,\n",
    "    filters for flood events, and creates GEOID.\n",
    "    \"\"\"\n",
    "    cols_to_keep = [\n",
    "        'BEGIN_YEARMONTH', 'BEGIN_DAY', 'STATE_FIPS', 'CZ_FIPS',\n",
    "        'EVENT_TYPE', 'FLOOD_CAUSE', 'BEGIN_LAT', 'BEGIN_LON'\n",
    "    ]\n",
    "    cols_to_drop = [ 'BEGIN_YEARMONTH', 'BEGIN_DAY', 'FLOOD_CAUSE', 'STATE_FIPS', 'CZ_FIPS', 'BEGIN_LAT', 'BEGIN_LON']\n",
    "    \n",
    "    df = (\n",
    "        pd.read_csv(path)\n",
    "          .query(\"STATE_FIPS == 12\")\n",
    "          .loc[:, cols_to_keep]\n",
    "          .assign(EVENT_TYPE=lambda d: d['EVENT_TYPE'].str.lower())\n",
    "          .query(\"EVENT_TYPE.str.contains('flood')\", engine='python')\n",
    "    )\n",
    "    \n",
    "    # Add GEOID column\n",
    "    df['GEOID'] = (\n",
    "        df['STATE_FIPS'].astype(str).str.zfill(2) +\n",
    "        df['CZ_FIPS'].astype(str).str.zfill(3)\n",
    "    )\n",
    "\n",
    "    df['date'] = pd.to_datetime(\n",
    "        df['BEGIN_YEARMONTH'].astype(str) + df['BEGIN_DAY'].astype(str).str.zfill(2),\n",
    "        format='%Y%m%d',\n",
    "        errors='coerce'\n",
    "    )\n",
    "    \n",
    "    df = df.drop(columns=cols_to_drop)\n",
    "    return df\n"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 303,
   "id": "f974e764-6fa6-4bbe-a8c1-a5fc4fa05d5b",
   "metadata": {},
   "outputs": [],
   "source": [
    "input_folder = \"datasets/storm_events\"\n",
    "\n",
    "\n",
    "data = pd.DataFrame()\n",
    "for filename in sorted(os.listdir(input_folder)):\n",
    "\n",
    "    if filename.endswith(\".csv\") or filename.endswith(\".csv.gz\"):\n",
    "\n",
    "        filepath = os.path.join(input_folder, filename)\n",
    "        \n",
    "        df = load_and_filter_storm_events(filepath)\n",
    "        data = pd.concat([data, df])"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 305,
   "id": "e8c2f068-4ee1-4888-8f3c-eca5b1684490",
   "metadata": {},
   "outputs": [],
   "source": [
    "data.to_csv(\"datasets/joined_counties/flood_events.csv\", index=False)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 47,
   "id": "cc8c1bd7-74b4-4431-b5db-c2eab1aba264",
   "metadata": {},
   "outputs": [
    {
     "data": {
      "text/html": [
       "<div>\n",
       "<style scoped>\n",
       "    .dataframe tbody tr th:only-of-type {\n",
       "        vertical-align: middle;\n",
       "    }\n",
       "\n",
       "    .dataframe tbody tr th {\n",
       "        vertical-align: top;\n",
       "    }\n",
       "\n",
       "    .dataframe thead th {\n",
       "        text-align: right;\n",
       "    }\n",
       "</style>\n",
       "<table border=\"1\" class=\"dataframe\">\n",
       "  <thead>\n",
       "    <tr style=\"text-align: right;\">\n",
       "      <th></th>\n",
       "      <th>EVENT_TYPE</th>\n",
       "      <th>GEOID</th>\n",
       "      <th>date</th>\n",
       "    </tr>\n",
       "  </thead>\n",
       "  <tbody>\n",
       "    <tr>\n",
       "      <th>375</th>\n",
       "      <td>coastal flood</td>\n",
       "      <td>12125</td>\n",
       "      <td>2015-12-05</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>563</th>\n",
       "      <td>flood</td>\n",
       "      <td>12087</td>\n",
       "      <td>2015-08-03</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>7934</th>\n",
       "      <td>flood</td>\n",
       "      <td>12057</td>\n",
       "      <td>2015-08-01</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>11779</th>\n",
       "      <td>flood</td>\n",
       "      <td>12017</td>\n",
       "      <td>2015-08-01</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>13330</th>\n",
       "      <td>flood</td>\n",
       "      <td>12101</td>\n",
       "      <td>2015-07-24</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>...</th>\n",
       "      <td>...</td>\n",
       "      <td>...</td>\n",
       "      <td>...</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>67500</th>\n",
       "      <td>flood</td>\n",
       "      <td>12031</td>\n",
       "      <td>2024-09-09</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>68223</th>\n",
       "      <td>flash flood</td>\n",
       "      <td>12031</td>\n",
       "      <td>2024-09-04</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>68429</th>\n",
       "      <td>flash flood</td>\n",
       "      <td>12031</td>\n",
       "      <td>2024-09-04</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>68430</th>\n",
       "      <td>flash flood</td>\n",
       "      <td>12031</td>\n",
       "      <td>2024-09-05</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>68903</th>\n",
       "      <td>coastal flood</td>\n",
       "      <td>12168</td>\n",
       "      <td>2024-11-16</td>\n",
       "    </tr>\n",
       "  </tbody>\n",
       "</table>\n",
       "<p>1780 rows × 3 columns</p>\n",
       "</div>"
      ],
      "text/plain": [
       "          EVENT_TYPE  GEOID       date\n",
       "375    coastal flood  12125 2015-12-05\n",
       "563            flood  12087 2015-08-03\n",
       "7934           flood  12057 2015-08-01\n",
       "11779          flood  12017 2015-08-01\n",
       "13330          flood  12101 2015-07-24\n",
       "...              ...    ...        ...\n",
       "67500          flood  12031 2024-09-09\n",
       "68223    flash flood  12031 2024-09-04\n",
       "68429    flash flood  12031 2024-09-04\n",
       "68430    flash flood  12031 2024-09-05\n",
       "68903  coastal flood  12168 2024-11-16\n",
       "\n",
       "[1780 rows x 3 columns]"
      ]
     },
     "execution_count": 47,
     "metadata": {},
     "output_type": "execute_result"
    }
   ],
   "source": [
    "data"
   ]
  },
  {
   "cell_type": "markdown",
   "id": "6892729e-67df-4e07-be27-ef70921c3140",
   "metadata": {},
   "source": [
    "# Merge Everything together"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 41,
   "id": "2ed0134e-d306-4450-a631-e50de0ddd45a",
   "metadata": {},
   "outputs": [],
   "source": [
    "slope_df = pd.read_csv(\"datasets/joined_counties/final_slope_counties.csv\")\n",
    "elev_df = pd.read_csv(\"datasets/joined_counties/final_elevation_counties.csv\")\n",
    "rainfall_df = pd.read_csv(\"datasets/joined_counties/rainfall_counties.csv.gz\")\n",
    "soil_moisture_df = pd.read_csv(\"datasets/joined_counties/soil_moisture_counties.csv.gz\")\n",
    "flood_events_df = pd.read_csv(\"datasets/joined_counties/flood_events.csv\")"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 363,
   "id": "600cb7e9-ab83-41b2-ba18-f7a297a278cb",
   "metadata": {},
   "outputs": [],
   "source": [
    "soil_features = elev_df.merge(slope_df, how=\"right\", on='GEOID')"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 364,
   "id": "febacac0-e323-4e75-b9d3-385a74b6a995",
   "metadata": {},
   "outputs": [
    {
     "data": {
      "text/html": [
       "<div>\n",
       "<style scoped>\n",
       "    .dataframe tbody tr th:only-of-type {\n",
       "        vertical-align: middle;\n",
       "    }\n",
       "\n",
       "    .dataframe tbody tr th {\n",
       "        vertical-align: top;\n",
       "    }\n",
       "\n",
       "    .dataframe thead th {\n",
       "        text-align: right;\n",
       "    }\n",
       "</style>\n",
       "<table border=\"1\" class=\"dataframe\">\n",
       "  <thead>\n",
       "    <tr style=\"text-align: right;\">\n",
       "      <th></th>\n",
       "      <th>GEOID</th>\n",
       "      <th>elev_min</th>\n",
       "      <th>elev_max</th>\n",
       "      <th>elev_mean</th>\n",
       "      <th>elev_std</th>\n",
       "      <th>slope_min</th>\n",
       "      <th>slope_max</th>\n",
       "      <th>slope_mean</th>\n",
       "      <th>slope_std</th>\n",
       "    </tr>\n",
       "  </thead>\n",
       "  <tbody>\n",
       "    <tr>\n",
       "      <th>0</th>\n",
       "      <td>12001</td>\n",
       "      <td>12</td>\n",
       "      <td>62</td>\n",
       "      <td>32.761905</td>\n",
       "      <td>12.895366</td>\n",
       "      <td>1.312327</td>\n",
       "      <td>16.027782</td>\n",
       "      <td>6.384000</td>\n",
       "      <td>4.614730</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>1</th>\n",
       "      <td>12003</td>\n",
       "      <td>20</td>\n",
       "      <td>57</td>\n",
       "      <td>37.761905</td>\n",
       "      <td>9.575514</td>\n",
       "      <td>0.328135</td>\n",
       "      <td>18.791857</td>\n",
       "      <td>7.266035</td>\n",
       "      <td>4.907126</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>2</th>\n",
       "      <td>12005</td>\n",
       "      <td>0</td>\n",
       "      <td>60</td>\n",
       "      <td>8.764706</td>\n",
       "      <td>14.116526</td>\n",
       "      <td>0.000000</td>\n",
       "      <td>5.646210</td>\n",
       "      <td>1.237601</td>\n",
       "      <td>1.635382</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>3</th>\n",
       "      <td>12007</td>\n",
       "      <td>26</td>\n",
       "      <td>62</td>\n",
       "      <td>47.000000</td>\n",
       "      <td>11.608187</td>\n",
       "      <td>1.995185</td>\n",
       "      <td>18.652594</td>\n",
       "      <td>8.575645</td>\n",
       "      <td>5.832273</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>4</th>\n",
       "      <td>12009</td>\n",
       "      <td>-2</td>\n",
       "      <td>25</td>\n",
       "      <td>4.170732</td>\n",
       "      <td>5.490457</td>\n",
       "      <td>0.000000</td>\n",
       "      <td>5.174222</td>\n",
       "      <td>1.286302</td>\n",
       "      <td>1.370454</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>...</th>\n",
       "      <td>...</td>\n",
       "      <td>...</td>\n",
       "      <td>...</td>\n",
       "      <td>...</td>\n",
       "      <td>...</td>\n",
       "      <td>...</td>\n",
       "      <td>...</td>\n",
       "      <td>...</td>\n",
       "      <td>...</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>62</th>\n",
       "      <td>12125</td>\n",
       "      <td>19</td>\n",
       "      <td>43</td>\n",
       "      <td>33.800000</td>\n",
       "      <td>10.183320</td>\n",
       "      <td>3.022486</td>\n",
       "      <td>14.101502</td>\n",
       "      <td>8.124914</td>\n",
       "      <td>4.005695</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>63</th>\n",
       "      <td>12127</td>\n",
       "      <td>-5</td>\n",
       "      <td>27</td>\n",
       "      <td>8.750000</td>\n",
       "      <td>7.972721</td>\n",
       "      <td>0.000000</td>\n",
       "      <td>6.106912</td>\n",
       "      <td>2.321718</td>\n",
       "      <td>1.863677</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>64</th>\n",
       "      <td>12129</td>\n",
       "      <td>0</td>\n",
       "      <td>29</td>\n",
       "      <td>10.772727</td>\n",
       "      <td>10.018705</td>\n",
       "      <td>0.000000</td>\n",
       "      <td>5.966317</td>\n",
       "      <td>1.835341</td>\n",
       "      <td>1.916657</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>65</th>\n",
       "      <td>12131</td>\n",
       "      <td>0</td>\n",
       "      <td>85</td>\n",
       "      <td>34.416667</td>\n",
       "      <td>30.319607</td>\n",
       "      <td>0.000000</td>\n",
       "      <td>4.687748</td>\n",
       "      <td>1.821154</td>\n",
       "      <td>1.472121</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>66</th>\n",
       "      <td>12133</td>\n",
       "      <td>12</td>\n",
       "      <td>82</td>\n",
       "      <td>29.937500</td>\n",
       "      <td>16.639186</td>\n",
       "      <td>1.037553</td>\n",
       "      <td>5.444872</td>\n",
       "      <td>2.852200</td>\n",
       "      <td>1.401803</td>\n",
       "    </tr>\n",
       "  </tbody>\n",
       "</table>\n",
       "<p>67 rows × 9 columns</p>\n",
       "</div>"
      ],
      "text/plain": [
       "    GEOID  elev_min  elev_max  elev_mean   elev_std  slope_min  slope_max  \\\n",
       "0   12001        12        62  32.761905  12.895366   1.312327  16.027782   \n",
       "1   12003        20        57  37.761905   9.575514   0.328135  18.791857   \n",
       "2   12005         0        60   8.764706  14.116526   0.000000   5.646210   \n",
       "3   12007        26        62  47.000000  11.608187   1.995185  18.652594   \n",
       "4   12009        -2        25   4.170732   5.490457   0.000000   5.174222   \n",
       "..    ...       ...       ...        ...        ...        ...        ...   \n",
       "62  12125        19        43  33.800000  10.183320   3.022486  14.101502   \n",
       "63  12127        -5        27   8.750000   7.972721   0.000000   6.106912   \n",
       "64  12129         0        29  10.772727  10.018705   0.000000   5.966317   \n",
       "65  12131         0        85  34.416667  30.319607   0.000000   4.687748   \n",
       "66  12133        12        82  29.937500  16.639186   1.037553   5.444872   \n",
       "\n",
       "    slope_mean  slope_std  \n",
       "0     6.384000   4.614730  \n",
       "1     7.266035   4.907126  \n",
       "2     1.237601   1.635382  \n",
       "3     8.575645   5.832273  \n",
       "4     1.286302   1.370454  \n",
       "..         ...        ...  \n",
       "62    8.124914   4.005695  \n",
       "63    2.321718   1.863677  \n",
       "64    1.835341   1.916657  \n",
       "65    1.821154   1.472121  \n",
       "66    2.852200   1.401803  \n",
       "\n",
       "[67 rows x 9 columns]"
      ]
     },
     "execution_count": 364,
     "metadata": {},
     "output_type": "execute_result"
    }
   ],
   "source": [
    "soil_features"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "3a4bba79-c8b2-4702-805a-2a863c8fea61",
   "metadata": {},
   "outputs": [],
   "source": []
  },
  {
   "cell_type": "code",
   "execution_count": 42,
   "id": "9e926026-f06a-4562-bb3e-59aca77bdb4f",
   "metadata": {},
   "outputs": [],
   "source": [
    "rainfall_df = rainfall_df[['GEOID', 'rainfall', 'date']]\n"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 40,
   "id": "b84af345-89b3-4f49-b26d-b4c1a9040e96",
   "metadata": {},
   "outputs": [],
   "source": [
    "rainfall_df['rainfall_rounded'] = round(rainfall_df['rainfall'])"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 37,
   "id": "1e91df88-b54a-460d-b6ef-bf2ca86df957",
   "metadata": {},
   "outputs": [
    {
     "data": {
      "text/plain": [
       "<Axes: >"
      ]
     },
     "execution_count": 37,
     "metadata": {},
     "output_type": "execute_result"
    },
    {
     "data": {
      "image/png": "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AADZCAsAIBthAQBkIywAgGyEBQCQjbAAALIRFgBANsICAMhGWAAA2QgLACAbYQEAZCMsAIBshAUAkI2wAACyERYAQDbCAgDIRlgAANkICwAgG2EBAGQjLACAbIQFAJCNsAAAshEWAEA2wgIAyEZYAADZCAsAIBthAQBkIywAgGyEBQCQjbAAALIRFgBANsICAMhGWAAA2QgLACAbYQEAZCMsAIBshAUAkI2wAACyqSos1qxZE3Pnzo2GhoZoaGiI5ubmeOyxxwZrbQBAwVQVFtOnT4877rgjtmzZElu2bImLL744rrjiiti5c+dgrQ8AKJAx1Zx8+eWX9/r4K1/5SqxZsyaefPLJOO+887IuDAAonqrC4q2OHDkSDzzwQBw6dCiam5v7PK9cLke5XO75uKOjIyIiKpVKVCqVE738UbrvqzQqDei8ouled1HX359ani3CfEVWy7NFmK/IhmO2gV6rLqXU/0/it9m+fXs0NzfHG2+8EaecckqsXbs2PvnJT/Z5fktLS6xateqo42vXro1x48ZVc2kAYJh0dnbG0qVLo729PRoaGvo8r+qwOHz4cOzduzdee+21ePDBB+M73/lObNq0Kc4999xjnn+sRyyampqira2t34VVq1KpRGtra9y6ZVSUu+r6PG9Hy6XZrjmUuudbtGhR1NfXD/dysqrl2SLMV2S1PFuE+YpsOGbr6OiIKVOmHDcsqn4qZOzYsXHOOedERMSCBQviqaeeiq9//evxz//8z8c8v1QqRalUOup4fX39oHwxyl11UT7Sd1gU/ZtrsL5uI0EtzxZhviKr5dkizFdkQznbQK/zjv+ORUqp1yMSAMC7V1WPWNx8882xZMmSaGpqioMHD8a6deti48aN8fjjjw/W+gCAAqkqLF5++eX4whe+EPv374+JEyfG3Llz4/HHH49FixYN1voAgAKpKizuueeewVoHAFADvFcIAJCNsAAAshEWAEA2wgIAyEZYAADZCAsAIBthAQBkIywAgGyEBQCQjbAAALIRFgBANsICAMhGWAAA2QgLACAbYQEAZCMsAIBshAUAkI2wAACyERYAQDbCAgDIRlgAANkICwAgG2EBAGQjLACAbIQFAJCNsAAAshEWAEA2wgIAyEZYAADZCAsAIBthAQBkIywAgGyEBQCQjbAAALIRFgBANsICAMhGWAAA2QgLACAbYQEA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SLznPe/pdfw973lPvPTSS8f8nNWrV8eqVauOOj5z5sxqLk1ELH2Hnz/lzizLAOBd7ODBgzFx4sQ+bz+hX96sq+v9/5hTSkcd63bTTTfFypUrez7u6uqKV199NSZPntzn55yIjo6OaGpqin379kVDQ0O2+x0panm+Wp4twnxFVsuzRZivyIZjtpRSHDx4MBobG/s9r6qwmDJlSowePfqoRycOHDhw1KMY3UqlUpRKpV7Hfud3fqeay1aloaGh5r6B3qqW56vl2SLMV2S1PFuE+YpsqGfr75GKblW9KmTs2LExf/78aG1t7XW8tbU1PvzhD1e3OgCg5lT9VMjKlSvjC1/4QixYsCCam5vjW9/6VuzduzeuueaawVgfAFAgVYfFVVddFa+88kr87d/+bezfvz9mz54d3/ve92LGjBmDsb4BK5VKcdtttx31tEutqOX5anm2CPMVWS3PFmG+IhvJs9Wl471uBABggLxXCACQjbAAALIRFgBANsICAMimZsLim9/8ZsycOTNOOumkmD9/fvzoRz8a7iVVraWlJerq6nr9mzp1as/tKaVoaWmJxsbGOPnkk2PhwoWxc+fOYVxx/zZv3hyXX355NDY2Rl1dXTz88MO9bh/IPOVyOVasWBFTpkyJ8ePHxx/90R/Fr3/96yGc4tiON9uf/dmfHbWXH/rQh3qdM1Jni/i/P8V/wQUXxIQJE+L000+PK6+8Mnbt2tXrnKLu30BmK/L+rVmzJubOndvzh5Oam5vjscce67m9qPvW7XjzFXnv3m716tVRV1cX119/fc+xQuxfqgHr1q1L9fX16dvf/nb6+c9/nq677ro0fvz49MILLwz30qpy2223pfPOOy/t37+/59+BAwd6br/jjjvShAkT0oMPPpi2b9+errrqqjRt2rTU0dExjKvu2/e+9710yy23pAcffDBFRFq/fn2v2wcyzzXXXJPe+973ptbW1vT000+niy66KM2bNy+9+eabQzxNb8ebbdmyZekTn/hEr7185ZVXep0zUmdLKaVLL7003XvvvWnHjh1p27Zt6bLLLktnnHFGev3113vOKer+DWS2Iu/fI488kh599NG0a9eutGvXrnTzzTen+vr6tGPHjpRScfet2/HmK/LevdV//dd/pTPPPDPNnTs3XXfddT3Hi7B/NREWf/AHf5CuueaaXsfe//73pxtvvHGYVnRibrvttjRv3rxj3tbV1ZWmTp2a7rjjjp5jb7zxRpo4cWL6p3/6pyFa4Yl7+w/fgczz2muvpfr6+rRu3bqec37zm9+kUaNGpccff3zI1n48fYXFFVdc0efnFGW2bgcOHEgRkTZt2pRSqq39e/tsKdXe/p166qnpO9/5Tk3t21t1z5dSbezdwYMH0+/+7u+m1tbW9LGPfawnLIqyf4V/KqT7rdwXL17c63h/b+U+ku3evTsaGxtj5syZ8Sd/8ifx/PPPR0TEnj174qWXXuo1Z6lUio997GOFnHMg82zdujUqlUqvcxobG2P27NmFmHnjxo1x+umnx6xZs+Iv//Iv48CBAz23FW229vb2iIiYNGlSRNTW/r19tm61sH9HjhyJdevWxaFDh6K5ubmm9i3i6Pm6FX3vli9fHpdddll8/OMf73W8KPt3Qu9uOpKcyFu5j1Qf/OAH4/77749Zs2bFyy+/HLfffnt8+MMfjp07d/bMcqw5X3jhheFY7jsykHleeumlGDt2bJx66qlHnTPS93bJkiXx2c9+NmbMmBF79uyJW2+9NS6++OLYunVrlEqlQs2WUoqVK1fGRz7ykZg9e3ZE1M7+HWu2iOLv3/bt26O5uTneeOONOOWUU2L9+vVx7rnn9vxgKfq+9TVfRPH3bt26dfH000/HU089ddRtRfnvXeHDols1b+U+Ui1ZsqTnP8+ZMyeam5vj7LPPjn/5l3/p+eWjWpjzrU5kniLMfNVVV/X859mzZ8eCBQtixowZ8eijj8anP/3pPj9vJM527bXXxrPPPhs//vGPj7qt6PvX12xF37/3ve99sW3btnjttdfiwQcfjGXLlsWmTZt6bi/6vvU137nnnlvovdu3b19cd911sWHDhjjppJP6PG+k71/hnwo5kbdyL4rx48fHnDlzYvfu3T2vDqmVOQcyz9SpU+Pw4cPx29/+ts9zimLatGkxY8aM2L17d0QUZ7YVK1bEI488Ek888URMnz6953gt7F9fsx1L0fZv7Nixcc4558SCBQti9erVMW/evPj6179eE/sW0fd8x1Kkvdu6dWscOHAg5s+fH2PGjIkxY8bEpk2b4h/+4R9izJgxPesb6ftX+LCo5bdyL5fL8dxzz8W0adNi5syZMXXq1F5zHj58ODZt2lTIOQcyz/z586O+vr7XOfv3748dO3YUbuZXXnkl9u3bF9OmTYuIkT9bSimuvfbaeOihh+KHP/xhzJw5s9ftRd6/4812LEXbv7dLKUW5XC70vvWne75jKdLeXXLJJbF9+/bYtm1bz78FCxbE5z//+di2bVucddZZxdi/IfkV0UHW/XLTe+65J/385z9P119/fRo/fnz61a9+NdxLq8qXvvSltHHjxvT888+nJ598Mn3qU59KEyZM6JnjjjvuSBMnTkwPPfRQ2r59e/rc5z43ol9uevDgwfTMM8+kZ555JkVEuuuuu9IzzzzT8zLggcxzzTXXpOnTp6cf/OAH6emnn04XX3zxiHhZWH+zHTx4MH3pS19KP/3pT9OePXvSE088kZqbm9N73/veQsyWUkp/9Vd/lSZOnJg2btzY62V7nZ2dPecUdf+ON1vR9++mm25KmzdvTnv27EnPPvtsuvnmm9OoUaPShg0bUkrF3bdu/c1X9L07lre+KiSlYuxfTYRFSin94z/+Y5oxY0YaO3Zs+v3f//1eLx0riu7XI9fX16fGxsb06U9/Ou3cubPn9q6urnTbbbelqVOnplKplD760Y+m7du3D+OK+/fEE0+kiDjq37Jly1JKA5vnf//3f9O1116bJk2alE4++eT0qU99Ku3du3cYpumtv9k6OzvT4sWL02mnnZbq6+vTGWeckZYtW3bUukfqbCmlY84WEenee+/tOaeo+3e82Yq+f3/+53/e87+Fp512Wrrkkkt6oiKl4u5bt/7mK/reHcvbw6II++dt0wGAbAr/OxYAwMghLACAbIQFAJCNsAAAshEWAEA2wgIAyEZYAADZCAsAIBthAQBkIywAgGyEBQCQjbAAALL5/wBRx5wFXGP1lQAAAABJRU5ErkJggg==",
      "text/plain": [
       "<Figure size 640x480 with 1 Axes>"
      ]
     },
     "metadata": {},
     "output_type": "display_data"
    }
   ],
   "source": [
    "rainfall_df['rainfall_rounded'].hist(bins=50)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "5a57dcf7-cb87-4968-9712-cb6335bdb097",
   "metadata": {},
   "outputs": [],
   "source": []
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "48534d21-6d21-45b4-a51a-5f97d6547c1d",
   "metadata": {},
   "outputs": [],
   "source": []
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "a968e21b-d8ad-471b-9c93-6c18aab5f502",
   "metadata": {},
   "outputs": [],
   "source": []
  },
  {
   "cell_type": "code",
   "execution_count": 44,
   "id": "50afda21-c2b9-458b-aef8-6cf225ea04e0",
   "metadata": {},
   "outputs": [
    {
     "data": {
      "image/png": "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BgaqtHXo0AHHjx/Hs2fPNC6Tm5uLrKwslRsRERFJ12sVbtLS0mBnZ6fSZmdnh7y8PNy9e1fjMpGRkbCwsFDeXFxcXkWpREREpCOvVbgBAJlMpnJfCKGxvdCECROQmZmpvKWkpFR6jURERKQ7Oj3nprTs7e2Rlpam0paeng4DAwNYWVlpXEYul0Mul7+K8oiIiKgKeK1mbvz8/BAbG6vStmvXLvj6+sLQ0FBHVREREVFVotNw8/DhQyQmJiIxMRHA80u9ExMTkZycDOD5IaX+/fsr+4eGhuL69esICwtDUlISli1bhqVLlyI8PFwX5RMREVEVpNPDUsePH0e7du2U98PCwgAAwcHBWLFiBVJTU5VBBwA8PDywbds2jB07FgsWLICjoyO+//57XgZORERESjoNN23btlWeEKzJihUr1NratGmDkydPVmJVRERE9Dp7rc65ISIiIioJww0RERFJCsMNERERSQrDDREREUkKww0RERFJCsMNERERSQrDDREREUkKww0RERFJCsMNERERSQrDDREREUkKww0RERFJCsMNERERSQrDDREREUkKww0RERFJCsMNERERSQrDDREREUkKww0RERFJCsMNERERSQrDDREREUkKww0RERFJCsMNERERSQrDDREREUkKww0RERFJCsMNERERSQrDDREREUkKww0RERFJCsMNERERSQrDDREREUkKww0RERFJCsMNERERSQrDDREREUkKww0RERFJCsMNERERSQrDDREREUkKww0RERFJCsMNERERSQrDDREREUkKww0RERFJCsMNERERSQrDDREREUkKww0RERFJCsMNERERSQrDDREREUkKww0RERFJCsMNERERSQrDDREREUkKww0RERFJCsMNERERSQrDDREREUkKww0RERFJCsMNERERSQrDDREREUmKzsNNVFQUPDw8oFAo4OPjg/j4+GL7r169Gt7e3jA2NoaDgwMGDhyIjIyMV1QtERERVXU6DTfr1q3DmDFjMHHiRJw6dQqtW7dGUFAQkpOTNfY/cOAA+vfvj5CQEJw/fx6//fYbjh07hsGDB7/iyomIiKiq0mm4mTt3LkJCQjB48GDUq1cP8+fPh4uLC6KjozX2P3z4MNzd3TF69Gh4eHjgrbfewtChQ3H8+PFXXDkRERFVVToLN0+fPsWJEycQGBio0h4YGIhD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",
      "text/plain": [
       "<Figure size 640x480 with 1 Axes>"
      ]
     },
     "metadata": {},
     "output_type": "display_data"
    },
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "Gamma distribution parameters: shape=0.4433551502488404, scale=18.039190224902658\n"
     ]
    },
    {
     "ename": "NameError",
     "evalue": "name 'data' is not defined",
     "output_type": "error",
     "traceback": [
      "\u001b[0;31m---------------------------------------------------------------------------\u001b[0m",
      "\u001b[0;31mNameError\u001b[0m                                 Traceback (most recent call last)",
      "Cell \u001b[0;32mIn[44], line 32\u001b[0m\n\u001b[1;32m     29\u001b[0m \u001b[38;5;28mprint\u001b[39m(\u001b[38;5;124mf\u001b[39m\u001b[38;5;124m\"\u001b[39m\u001b[38;5;124mGamma distribution parameters: shape=\u001b[39m\u001b[38;5;132;01m{\u001b[39;00mshape\u001b[38;5;132;01m}\u001b[39;00m\u001b[38;5;124m, scale=\u001b[39m\u001b[38;5;132;01m{\u001b[39;00mscale\u001b[38;5;132;01m}\u001b[39;00m\u001b[38;5;124m\"\u001b[39m)\n\u001b[1;32m     31\u001b[0m \u001b[38;5;66;03m# Example: Train a Random Forest to predict rainy days\u001b[39;00m\n\u001b[0;32m---> 32\u001b[0m X \u001b[38;5;241m=\u001b[39m data[[\u001b[38;5;124m'\u001b[39m\u001b[38;5;124mtemperature\u001b[39m\u001b[38;5;124m'\u001b[39m, \u001b[38;5;124m'\u001b[39m\u001b[38;5;124mhumidity\u001b[39m\u001b[38;5;124m'\u001b[39m, \u001b[38;5;124m'\u001b[39m\u001b[38;5;124mpressure\u001b[39m\u001b[38;5;124m'\u001b[39m]]  \u001b[38;5;66;03m# Example features\u001b[39;00m\n\u001b[1;32m     33\u001b[0m y \u001b[38;5;241m=\u001b[39m is_rainy\n\u001b[1;32m     34\u001b[0m X_train, X_test, y_train, y_test \u001b[38;5;241m=\u001b[39m train_test_split(X, y, test_size\u001b[38;5;241m=\u001b[39m\u001b[38;5;241m0.3\u001b[39m, random_state\u001b[38;5;241m=\u001b[39m\u001b[38;5;241m42\u001b[39m)\n",
      "\u001b[0;31mNameError\u001b[0m: name 'data' is not defined"
     ]
    }
   ],
   "source": [
    "import numpy as np\n",
    "import pandas as pd\n",
    "import matplotlib.pyplot as plt\n",
    "from scipy.stats import gamma\n",
    "from sklearn.ensemble import RandomForestClassifier\n",
    "from sklearn.model_selection import train_test_split\n",
    "\n",
    "# Load IMERG data (assuming a CSV with daily precipitation)\n",
    "\n",
    "precip = rainfall_df['rainfall']  # Daily precipitation in mm\n",
    "\n",
    "# Handle zeros and non-zeros separately\n",
    "is_rainy = (precip > 0).astype(int)  # Binary indicator for rain\n",
    "nonzero_precip = precip[precip > 0]  # Non-zero precipitation values\n",
    "\n",
    "# Log-transform non-zero values\n",
    "log_nonzero_precip = np.log1p(nonzero_precip)\n",
    "\n",
    "# Visualize distribution\n",
    "plt.hist(log_nonzero_precip, bins=50, density=True, alpha=0.7, label='Log-transformed')\n",
    "plt.title('Distribution of Log-Transformed Non-Zero Precipitation')\n",
    "plt.xlabel('Log(Precipitation + 1)')\n",
    "plt.ylabel('Density')\n",
    "plt.legend()\n",
    "plt.show()\n",
    "\n",
    "# Fit a gamma distribution to non-zero precipitation\n",
    "shape, loc, scale = gamma.fit(nonzero_precip, floc=0)  # Fix location to 0\n",
    "print(f\"Gamma distribution parameters: shape={shape}, scale={scale}\")\n",
    "\n",
    "# Example: Train a Random Forest to predict rainy days\n",
    "X = rain[['temperature', 'humidity', 'pressure']]  # Example features\n",
    "y = is_rainy\n",
    "X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)\n",
    "model = RandomForestClassifier(class_weight='balanced', random_state=42)\n",
    "model.fit(X_train, y_train)\n",
    "print(f\"Model accuracy: {model.score(X_test, y_test)}\")"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "72178558-aeaa-4280-9d5d-3115fdffe368",
   "metadata": {},
   "outputs": [],
   "source": []
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "6c436c1c-5bcc-48cc-99a8-21793d6f18bc",
   "metadata": {},
   "outputs": [],
   "source": []
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "75f2793b-ead3-4eb4-b0a9-497e9f80d17c",
   "metadata": {},
   "outputs": [],
   "source": []
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "4e064acd-ab0c-4c35-bedc-10c32f59be86",
   "metadata": {},
   "outputs": [],
   "source": []
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "edd3744a-14e2-4285-bae1-08b9ad84a77e",
   "metadata": {},
   "outputs": [],
   "source": []
  },
  {
   "cell_type": "code",
   "execution_count": 397,
   "id": "5151a116-0efa-414d-8131-50c09171eae4",
   "metadata": {},
   "outputs": [],
   "source": [
    "rainfall_df = rainfall_df.groupby([\"GEOID\", \"date\"], as_index=False)['rainfall'].sum()"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 399,
   "id": "597ce818-255e-4eed-b0a1-e0e41097f788",
   "metadata": {},
   "outputs": [
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "        GEOID        date     rainfall\n",
      "157967  12087  2017-06-07  11811.97978\n"
     ]
    }
   ],
   "source": [
    "print(rainfall_df[rainfall_df['rainfall']== rainfall_df['rainfall'].max()])"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 393,
   "id": "a90a816c-cf39-4829-b08a-b4b68b6c9bd3",
   "metadata": {},
   "outputs": [
    {
     "data": {
      "text/plain": [
       "<Axes: >"
      ]
     },
     "execution_count": 393,
     "metadata": {},
     "output_type": "execute_result"
    },
    {
     "data": {
      "image/png": "iVBORw0KGgoAAAANSUhEUgAAAkcAAAGdCAYAAAAYDtcjAAAAOXRFWHRTb2Z0d2FyZQBNYXRwbG90bGliIHZlcnNpb24zLjkuMiwgaHR0cHM6Ly9tYXRwbG90bGliLm9yZy8hTgPZAAAACXBIWXMAAA9hAAAPYQGoP6dpAABL10lEQVR4nO3de1gU56E/8C/eiHJwK1og25DEnpNjTbH5pSRVbFqTaNQe0aY5p7loadJak9So5URPEk9Oqk0bNSZRG4mpsVZNvKWtmrsoeEFREAVRQEVUFBAWEJcFFHa5vL8/DOMs173M7Mzsfj/Ps8+ju+/Ovjvszn7nnfcSJIQQICIiIiIAQC+tK0BERESkJwxHRERERDIMR0REREQyDEdEREREMgxHRERERDIMR0REREQyDEdEREREMgxHRERERDJ9tK6AllpbW1FWVobQ0FAEBQVpXR0iIiJygRACdXV1MJvN6NVL+XaegA5HZWVliIqK0roaRERE5IGSkhLcdtttim83oMNRaGgogBs7d+DAgRrXhoiIiFxRW1uLqKgo6XdcaQEdjtoupQ0cOJDhiIiIyGDU6hLDDtlEREREMgxHRERERDIMR0REREQyDEdEREREMm6HowMHDmDy5Mkwm80ICgrCJ598Ij3W1NSEl19+GSNGjEBISAjMZjN++ctfoqyszGkbdrsds2fPxpAhQxASEoIpU6agtLTUqYzVakV8fDxMJhNMJhPi4+NRU1PjVKa4uBiTJ09GSEgIhgwZgjlz5sDhcLj7loiIiIgkboeja9eu4Z577kFiYmKHx65fv47s7Gy89tpryM7Oxvbt23H27FlMmTLFqVxCQgJ27NiBrVu3Ii0tDfX19YiLi0NLS4tUZurUqcjJyUFSUhKSkpKQk5OD+Ph46fGWlhZMmjQJ165dQ1paGrZu3Ypt27Zh7ty57r4lIiIiopuEFwCIHTt2dFsmMzNTABCXLl0SQghRU1Mj+vbtK7Zu3SqVuXz5sujVq5dISkoSQghx6tQpAUBkZGRIZdLT0wUAcebMGSGEEF999ZXo1auXuHz5slRmy5YtIjg4WNhsNpfqb7PZBACXyxMREZH21P79Vr3Pkc1mQ1BQEL7xjW8AALKystDU1ITx48dLZcxmM6Kjo3H48GEAQHp6OkwmE0aOHCmVGTVqFEwmk1OZ6OhomM1mqcyECRNgt9uRlZXVaV3sdjtqa2udbkRERERyqoajxsZGvPLKK5g6dao0yaLFYkG/fv0waNAgp7IRERGwWCxSmfDw8A7bCw8PdyoTERHh9PigQYPQr18/qUx7ixcvlvowmUwmLh1CREREHagWjpqamvDkk0+itbUVq1at6rG8EMJppsvOZr30pIzc/PnzYbPZpFtJSYkrb4WIiIgCiCrhqKmpCY8//jiKioqQnJzstDRHZGQkHA4HrFar03MqKyullqDIyEhUVFR02G5VVZVTmfYtRFarFU1NTR1alNoEBwdLS4VwyRAiIiLqjOLhqC0YFRYWIiUlBYMHD3Z6PCYmBn379kVycrJ0X3l5OfLy8jB69GgAQGxsLGw2GzIzM6UyR44cgc1mcyqTl5eH8vJyqczu3bsRHByMmJgYpd8WERERBQi3F56tr6/HuXPnpP8XFRUhJycHYWFhMJvN+K//+i9kZ2fjiy++QEtLi9S6ExYWhn79+sFkMmH69OmYO3cuBg8ejLCwMMybNw8jRozAuHHjAADDhw/HxIkTMWPGDKxevRoA8OyzzyIuLg7Dhg0DAIwfPx5333034uPj8dZbb+Hq1auYN28eZsyYwRYhIiIAjU0t+Cj9Eh76Tjj+LfxftK4OkXG4O7xt3759AkCH29NPPy2Kioo6fQyA2Ldvn7SNhoYGMWvWLBEWFib69+8v4uLiRHFxsdPrVFdXi2nTponQ0FARGhoqpk2bJqxWq1OZS5cuiUmTJon+/fuLsLAwMWvWLNHY2Ojye+FQfiLyZ2/uPC3uePkLccfLX2hdFSJFqf37HSSEEJqkMh2ora2FyWSCzWZjaxMR+Z0nVqfjSNFVAMDFJZM0rg2RctT+/ebaakREREQyDEdEREREMgxHRERERDIMR0REREQyDEdEREREMgxHRERERDIMR0REREQyDEdEREREMgxHRERERDIMR0REREQyDEdEREREMgxHRERERDIMR0REREQyDEdEREREMgxHRERERDIMR0REREQyDEdEREREMgxHRERERDIMR0REREQyDEdEREREMgxHRERERDIMR0REREQyDEdEREREMgxHRERERDIMR0REREQyDEdEREREMgxHRERERDIMR0REREQyDEdEREREMgxHRERERDIMR0REREQyDEdERAFg4ooD+DTnstbVIDIEhiMiogBwxlKH323N0boaRIbAcEREREQkw3BEREREJMNwRERERCTDcEREREQkw3BEREREJMNwRERERCTDcEREFEAqahuxNbMYDY4WratCpFt9tK4AERH5zk8TD8FS24gzljosnPJdratDpEtsOSIiCiCW2kYAwN4zlRrXhEi/GI6IiIiIZBiOiIiIiGQYjoiIiIhkGI6IiIiIZNwORwcOHMDkyZNhNpsRFBSETz75xOlxIQQWLlwIs9mM/v3748EHH0R+fr5TGbvdjtmzZ2PIkCEICQnBlClTUFpa6lTGarUiPj4eJpMJJpMJ8fHxqKmpcSpTXFyMyZMnIyQkBEOGDMGcOXPgcDjcfUtERH7pUvV1ratAZEhuh6Nr167hnnvuQWJiYqePL126FMuWLUNiYiKOHj2KyMhIPPLII6irq5PKJCQkYMeOHdi6dSvS0tJQX1+PuLg4tLTcnHdj6tSpyMnJQVJSEpKSkpCTk4P4+Hjp8ZaWFkyaNAnXrl1DWloatm7dim3btmHu3LnuviUiIr/UNjKNiNwTJIQQHj85KAg7duzAo48+CuBGq5HZbEZCQgJefvllADdaiSIiIvDmm2/iueeeg81mwze/+U189NFHeOKJJwAAZWVliIqKwldffYUJEybg9OnTuPvuu5GRkYGRI0cCADIyMhAbG4szZ85g2LBh2LlzJ+Li4lBSUgKz2QwA2Lp1K5555hlUVlZi4MCBPda/trYWJpMJNpvNpfJEREZy5ytfdvnY7WEDcOClh3xYGyLlqP37rWifo6KiIlgsFowfP166Lzg4GGPGjMHhw4cBAFlZWWhqanIqYzabER0dLZVJT0+HyWSSghEAjBo1CiaTyalMdHS0FIwAYMKECbDb7cjKyuq0fna7HbW1tU43IiIiIjlFw5HFYgEAREREON0fEREhPWaxWNCvXz8MGjSo2zLh4eEdth8eHu5Upv3rDBo0CP369ZPKtLd48WKpD5PJZEJUVJQH75KIiIj8mSqj1YKCgpz+L4TocF977ct0Vt6TMnLz58+HzWaTbiUlJd3WiYiIiAKPouEoMjISADq03FRWVkqtPJGRkXA4HLBard2Wqaio6LD9qqoqpzLtX8dqtaKpqalDi1Kb4OBgDBw40OlGREREJKdoOBo6dCgiIyORnJws3edwOJCamorRo0cDAGJiYtC3b1+nMuXl5cjLy5PKxMbGwmazITMzUypz5MgR2Gw2pzJ5eXkoLy+XyuzevRvBwcGIiYlR8m0RERFRAOnj7hPq6+tx7tw56f9FRUXIyclBWFgYbr/9diQkJGDRokW46667cNddd2HRokUYMGAApk6dCgAwmUyYPn065s6di8GDByMsLAzz5s3DiBEjMG7cOADA8OHDMXHiRMyYMQOrV68GADz77LOIi4vDsGHDAADjx4/H3Xffjfj4eLz11lu4evUq5s2bhxkzZrBFiIiIiDzmdjg6duwYHnro5vDPF198EQDw9NNPY/369XjppZfQ0NCAmTNnwmq1YuTIkdi9ezdCQ0Ol5yxfvhx9+vTB448/joaGBowdOxbr169H7969pTKbNm3CnDlzpFFtU6ZMcZpbqXfv3vjyyy8xc+ZM/PCHP0T//v0xdepUvP322+7vBSIiIqKveTXPkdFxniMi8mfdzXMEABeXTPJRTYiUZah5joiIiIiMjuGIiIiISIbhiIiIiEiG4YiIiIhIhuGIiIiISIbhiIiIiEiG4YiIyA85mlu1rgKRYTEcERH5mZySGvz7/+3UuhpEhsVwRETkZ17/PF/rKhAZGsMRERERkQzDEREREZEMwxERERGRDMMRERERkQzDEREREZEMwxERERGRDMMRERERkQzDEREREZEMwxERERGRDMMRERERkQzDERGRnxFaV4DI4BiOiIj8jGA6IvIKwxERERGRDMMRERERkQzDEREREZEMwxERERGRDMMRERERkQzDEREREZEMwxERERGRDMMRERERkQzDEREREZEMwxERkZ/hBNlE3mE4IiLyNwZeP6S5pRVv7yrA4fNXtK4KBTCGIyIi0o0tR0uQuO8cpq45onVVKIAxHBERkW5cvHJN6yoQMRwRERERyTEcEREREckwHBERERHJMBwRERERyTAcEREREckwHBERERHJMBwRERERyTAcERH5GePOj02kDwxHRERERDIMR0REfsbAS6sR6QLDEREREZEMwxERERGRjOLhqLm5Gf/3f/+HoUOHon///vj2t7+N119/Ha2trVIZIQQWLlwIs9mM/v3748EHH0R+fr7Tdux2O2bPno0hQ4YgJCQEU6ZMQWlpqVMZq9WK+Ph4mEwmmEwmxMfHo6amRum3RERERAFE8XD05ptv4i9/+QsSExNx+vRpLF26FG+99RZWrlwplVm6dCmWLVuGxMREHD16FJGRkXjk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nIbi7t69G2azGXfeeafyO0AHqqurUVJSgltvvRUA97c7hBCYNWsWtm/fjr1792Lo0KFOj/Pzrbye9nlnDP8Zd6nbNrmsbSj/2rVrxalTp0RCQoIICQkRFy9e1LpqujJ37lyxf/9+ceHCBZGRkSHi4uJEaGiotJ+WLFkiTCaT2L59u8jNzRVPPfVUp0Nxb7vtNpGSkiKys7PFww8/3Omw0O9973siPT1dpKenixEjRnQ6LHTs2LEiOztbpKSkiNtuu83wQ/nr6urE8ePHxfHjxwUAsWzZMnH8+HFpSgk97d+amhoREREhnnrqKZGbmyu2b98uBg4caKihzt3t77q6OjF37lxx+PBhUVRUJPbt2ydiY2PFt771Le5vD/z2t78VJpNJ7N+/32nY+PXr16Uy/Hwrq6d97o+fcYYjFbz33nvijjvuEP369RPf//73nYY70g1t84707dtXmM1m8dhjj4n8/Hzp8dbWVrFgwQIRGRkpgoODxY9//GORm5vrtI2GhgYxa9YsERYWJvr37y/i4uJEcXGxU5nq6moxbdo0ERoaKkJDQ8W0adOE1Wp1KnPp0iUxadIk0b9/fxEWFiZmzZrlNATUiPbt2ycAdLg9/fTTQgj97d+TJ0+KH/3oRyI4OFhERkaKhQsXGmqYc3f7+/r162L8+PHim9/8pujbt6+4/fbbxdNPP91hX3J/u6az/QxArFu3TirDz7eyetrn/vgZD/r6jRMRERER2OeIiIiIyAnDEREREZEMwxERERGRDMMRERERkQzDEREREZEMwxERERGRDMMRERERkQzDEREREZEMwxERERGRDMMRERERkQzDEREREZEMwxERERGRzP8Hz1hwMWeJOhkAAAAASUVORK5CYII=",
      "text/plain": [
       "<Figure size 640x480 with 1 Axes>"
      ]
     },
     "metadata": {},
     "output_type": "display_data"
    }
   ],
   "source": [
    "rainfall_df['rainfall'].plot()"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 368,
   "id": "28d1726a-b863-4da9-83ed-52e92a888273",
   "metadata": {},
   "outputs": [],
   "source": [
    "soil_moisture_df = soil_moisture_df[['GEOID', 'soil_moisture', 'date']]"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 369,
   "id": "b2f53ec6-8e76-4870-b1f3-8c15f3f7141c",
   "metadata": {},
   "outputs": [],
   "source": [
    "soil_moisture_df = soil_moisture_df.groupby([\"GEOID\", \"date\"], as_index=False)['soil_moisture'].mean()"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 370,
   "id": "428fb1e4-1e67-4c95-9508-5c63c1eb77c2",
   "metadata": {},
   "outputs": [
    {
     "data": {
      "text/html": [
       "<div>\n",
       "<style scoped>\n",
       "    .dataframe tbody tr th:only-of-type {\n",
       "        vertical-align: middle;\n",
       "    }\n",
       "\n",
       "    .dataframe tbody tr th {\n",
       "        vertical-align: top;\n",
       "    }\n",
       "\n",
       "    .dataframe thead th {\n",
       "        text-align: right;\n",
       "    }\n",
       "</style>\n",
       "<table border=\"1\" class=\"dataframe\">\n",
       "  <thead>\n",
       "    <tr style=\"text-align: right;\">\n",
       "      <th></th>\n",
       "      <th>GEOID</th>\n",
       "      <th>date</th>\n",
       "      <th>soil_moisture</th>\n",
       "    </tr>\n",
       "  </thead>\n",
       "  <tbody>\n",
       "    <tr>\n",
       "      <th>0</th>\n",
       "      <td>12001</td>\n",
       "      <td>2015-04-01</td>\n",
       "      <td>0.154073</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>1</th>\n",
       "      <td>12001</td>\n",
       "      <td>2015-04-04</td>\n",
       "      <td>0.149908</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>2</th>\n",
       "      <td>12001</td>\n",
       "      <td>2015-04-06</td>\n",
       "      <td>0.182036</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>3</th>\n",
       "      <td>12001</td>\n",
       "      <td>2015-04-07</td>\n",
       "      <td>0.178972</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>4</th>\n",
       "      <td>12001</td>\n",
       "      <td>2015-04-09</td>\n",
       "      <td>0.159802</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>...</th>\n",
       "      <td>...</td>\n",
       "      <td>...</td>\n",
       "      <td>...</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>103215</th>\n",
       "      <td>12133</td>\n",
       "      <td>2024-12-19</td>\n",
       "      <td>0.279998</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>103216</th>\n",
       "      <td>12133</td>\n",
       "      <td>2024-12-22</td>\n",
       "      <td>0.245652</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>103217</th>\n",
       "      <td>12133</td>\n",
       "      <td>2024-12-25</td>\n",
       "      <td>0.222334</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>103218</th>\n",
       "      <td>12133</td>\n",
       "      <td>2024-12-27</td>\n",
       "      <td>0.274217</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>103219</th>\n",
       "      <td>12133</td>\n",
       "      <td>2024-12-30</td>\n",
       "      <td>0.373461</td>\n",
       "    </tr>\n",
       "  </tbody>\n",
       "</table>\n",
       "<p>103220 rows × 3 columns</p>\n",
       "</div>"
      ],
      "text/plain": [
       "        GEOID        date  soil_moisture\n",
       "0       12001  2015-04-01       0.154073\n",
       "1       12001  2015-04-04       0.149908\n",
       "2       12001  2015-04-06       0.182036\n",
       "3       12001  2015-04-07       0.178972\n",
       "4       12001  2015-04-09       0.159802\n",
       "...       ...         ...            ...\n",
       "103215  12133  2024-12-19       0.279998\n",
       "103216  12133  2024-12-22       0.245652\n",
       "103217  12133  2024-12-25       0.222334\n",
       "103218  12133  2024-12-27       0.274217\n",
       "103219  12133  2024-12-30       0.373461\n",
       "\n",
       "[103220 rows x 3 columns]"
      ]
     },
     "execution_count": 370,
     "metadata": {},
     "output_type": "execute_result"
    }
   ],
   "source": [
    "soil_moisture_df"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 371,
   "id": "0bc85493-5d58-4aaf-ace3-666a580a75c7",
   "metadata": {},
   "outputs": [
    {
     "data": {
      "text/html": [
       "<div>\n",
       "<style scoped>\n",
       "    .dataframe tbody tr th:only-of-type {\n",
       "        vertical-align: middle;\n",
       "    }\n",
       "\n",
       "    .dataframe tbody tr th {\n",
       "        vertical-align: top;\n",
       "    }\n",
       "\n",
       "    .dataframe thead th {\n",
       "        text-align: right;\n",
       "    }\n",
       "</style>\n",
       "<table border=\"1\" class=\"dataframe\">\n",
       "  <thead>\n",
       "    <tr style=\"text-align: right;\">\n",
       "      <th></th>\n",
       "      <th>EVENT_TYPE</th>\n",
       "      <th>GEOID</th>\n",
       "      <th>date</th>\n",
       "    </tr>\n",
       "  </thead>\n",
       "  <tbody>\n",
       "    <tr>\n",
       "      <th>0</th>\n",
       "      <td>coastal flood</td>\n",
       "      <td>12125</td>\n",
       "      <td>2015-12-05</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>1</th>\n",
       "      <td>flood</td>\n",
       "      <td>12087</td>\n",
       "      <td>2015-08-03</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>2</th>\n",
       "      <td>flood</td>\n",
       "      <td>12057</td>\n",
       "      <td>2015-08-01</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>3</th>\n",
       "      <td>flood</td>\n",
       "      <td>12017</td>\n",
       "      <td>2015-08-01</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>4</th>\n",
       "      <td>flood</td>\n",
       "      <td>12101</td>\n",
       "      <td>2015-07-24</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>...</th>\n",
       "      <td>...</td>\n",
       "      <td>...</td>\n",
       "      <td>...</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>1775</th>\n",
       "      <td>flood</td>\n",
       "      <td>12031</td>\n",
       "      <td>2024-09-09</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>1776</th>\n",
       "      <td>flash flood</td>\n",
       "      <td>12031</td>\n",
       "      <td>2024-09-04</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>1777</th>\n",
       "      <td>flash flood</td>\n",
       "      <td>12031</td>\n",
       "      <td>2024-09-04</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>1778</th>\n",
       "      <td>flash flood</td>\n",
       "      <td>12031</td>\n",
       "      <td>2024-09-05</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>1779</th>\n",
       "      <td>coastal flood</td>\n",
       "      <td>12168</td>\n",
       "      <td>2024-11-16</td>\n",
       "    </tr>\n",
       "  </tbody>\n",
       "</table>\n",
       "<p>1780 rows × 3 columns</p>\n",
       "</div>"
      ],
      "text/plain": [
       "         EVENT_TYPE  GEOID        date\n",
       "0     coastal flood  12125  2015-12-05\n",
       "1             flood  12087  2015-08-03\n",
       "2             flood  12057  2015-08-01\n",
       "3             flood  12017  2015-08-01\n",
       "4             flood  12101  2015-07-24\n",
       "...             ...    ...         ...\n",
       "1775          flood  12031  2024-09-09\n",
       "1776    flash flood  12031  2024-09-04\n",
       "1777    flash flood  12031  2024-09-04\n",
       "1778    flash flood  12031  2024-09-05\n",
       "1779  coastal flood  12168  2024-11-16\n",
       "\n",
       "[1780 rows x 3 columns]"
      ]
     },
     "execution_count": 371,
     "metadata": {},
     "output_type": "execute_result"
    }
   ],
   "source": [
    "flood_events_df"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 372,
   "id": "defb5337-2a37-4cd3-9dae-a6c31421e3c7",
   "metadata": {},
   "outputs": [],
   "source": [
    "soil_rain = soil_moisture_df.merge(rainfall_df, how=\"inner\", on=['GEOID', 'date'])"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 373,
   "id": "a135fd7d-1bc9-4325-aef4-baa81e3fbfec",
   "metadata": {},
   "outputs": [],
   "source": [
    "soil_rain_elev = soil_rain.merge(soil_features, how=\"inner\", on=\"GEOID\")"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 374,
   "id": "b2c38040-8782-4b23-9988-7b97504bc837",
   "metadata": {},
   "outputs": [
    {
     "data": {
      "text/html": [
       "<div>\n",
       "<style scoped>\n",
       "    .dataframe tbody tr th:only-of-type {\n",
       "        vertical-align: middle;\n",
       "    }\n",
       "\n",
       "    .dataframe tbody tr th {\n",
       "        vertical-align: top;\n",
       "    }\n",
       "\n",
       "    .dataframe thead th {\n",
       "        text-align: right;\n",
       "    }\n",
       "</style>\n",
       "<table border=\"1\" class=\"dataframe\">\n",
       "  <thead>\n",
       "    <tr style=\"text-align: right;\">\n",
       "      <th></th>\n",
       "      <th>GEOID</th>\n",
       "      <th>date</th>\n",
       "      <th>soil_moisture</th>\n",
       "      <th>rainfall</th>\n",
       "      <th>elev_min</th>\n",
       "      <th>elev_max</th>\n",
       "      <th>elev_mean</th>\n",
       "      <th>elev_std</th>\n",
       "      <th>slope_min</th>\n",
       "      <th>slope_max</th>\n",
       "      <th>slope_mean</th>\n",
       "      <th>slope_std</th>\n",
       "    </tr>\n",
       "  </thead>\n",
       "  <tbody>\n",
       "    <tr>\n",
       "      <th>0</th>\n",
       "      <td>12001</td>\n",
       "      <td>2015-04-01</td>\n",
       "      <td>0.154073</td>\n",
       "      <td>0.225000</td>\n",
       "      <td>12</td>\n",
       "      <td>62</td>\n",
       "      <td>32.761905</td>\n",
       "      <td>12.895366</td>\n",
       "      <td>1.312327</td>\n",
       "      <td>16.027782</td>\n",
       "      <td>6.3840</td>\n",
       "      <td>4.614730</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>1</th>\n",
       "      <td>12001</td>\n",
       "      <td>2015-04-04</td>\n",
       "      <td>0.149908</td>\n",
       "      <td>40.025000</td>\n",
       "      <td>12</td>\n",
       "      <td>62</td>\n",
       "      <td>32.761905</td>\n",
       "      <td>12.895366</td>\n",
       "      <td>1.312327</td>\n",
       "      <td>16.027782</td>\n",
       "      <td>6.3840</td>\n",
       "      <td>4.614730</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>2</th>\n",
       "      <td>12001</td>\n",
       "      <td>2015-04-06</td>\n",
       "      <td>0.182036</td>\n",
       "      <td>46.364998</td>\n",
       "      <td>12</td>\n",
       "      <td>62</td>\n",
       "      <td>32.761905</td>\n",
       "      <td>12.895366</td>\n",
       "      <td>1.312327</td>\n",
       "      <td>16.027782</td>\n",
       "      <td>6.3840</td>\n",
       "      <td>4.614730</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>3</th>\n",
       "      <td>12001</td>\n",
       "      <td>2015-04-07</td>\n",
       "      <td>0.178972</td>\n",
       "      <td>13.530000</td>\n",
       "      <td>12</td>\n",
       "      <td>62</td>\n",
       "      <td>32.761905</td>\n",
       "      <td>12.895366</td>\n",
       "      <td>1.312327</td>\n",
       "      <td>16.027782</td>\n",
       "      <td>6.3840</td>\n",
       "      <td>4.614730</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>4</th>\n",
       "      <td>12001</td>\n",
       "      <td>2015-04-09</td>\n",
       "      <td>0.159802</td>\n",
       "      <td>0.180000</td>\n",
       "      <td>12</td>\n",
       "      <td>62</td>\n",
       "      <td>32.761905</td>\n",
       "      <td>12.895366</td>\n",
       "      <td>1.312327</td>\n",
       "      <td>16.027782</td>\n",
       "      <td>6.3840</td>\n",
       "      <td>4.614730</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>...</th>\n",
       "      <td>...</td>\n",
       "      <td>...</td>\n",
       "      <td>...</td>\n",
       "      <td>...</td>\n",
       "      <td>...</td>\n",
       "      <td>...</td>\n",
       "      <td>...</td>\n",
       "      <td>...</td>\n",
       "      <td>...</td>\n",
       "      <td>...</td>\n",
       "      <td>...</td>\n",
       "      <td>...</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>103156</th>\n",
       "      <td>12133</td>\n",
       "      <td>2024-12-19</td>\n",
       "      <td>0.279998</td>\n",
       "      <td>0.000000</td>\n",
       "      <td>12</td>\n",
       "      <td>82</td>\n",
       "      <td>29.937500</td>\n",
       "      <td>16.639186</td>\n",
       "      <td>1.037553</td>\n",
       "      <td>5.444872</td>\n",
       "      <td>2.8522</td>\n",
       "      <td>1.401803</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>103157</th>\n",
       "      <td>12133</td>\n",
       "      <td>2024-12-22</td>\n",
       "      <td>0.245652</td>\n",
       "      <td>0.000000</td>\n",
       "      <td>12</td>\n",
       "      <td>82</td>\n",
       "      <td>29.937500</td>\n",
       "      <td>16.639186</td>\n",
       "      <td>1.037553</td>\n",
       "      <td>5.444872</td>\n",
       "      <td>2.8522</td>\n",
       "      <td>1.401803</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>103158</th>\n",
       "      <td>12133</td>\n",
       "      <td>2024-12-25</td>\n",
       "      <td>0.222334</td>\n",
       "      <td>20.055000</td>\n",
       "      <td>12</td>\n",
       "      <td>82</td>\n",
       "      <td>29.937500</td>\n",
       "      <td>16.639186</td>\n",
       "      <td>1.037553</td>\n",
       "      <td>5.444872</td>\n",
       "      <td>2.8522</td>\n",
       "      <td>1.401803</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>103159</th>\n",
       "      <td>12133</td>\n",
       "      <td>2024-12-27</td>\n",
       "      <td>0.274217</td>\n",
       "      <td>0.000000</td>\n",
       "      <td>12</td>\n",
       "      <td>82</td>\n",
       "      <td>29.937500</td>\n",
       "      <td>16.639186</td>\n",
       "      <td>1.037553</td>\n",
       "      <td>5.444872</td>\n",
       "      <td>2.8522</td>\n",
       "      <td>1.401803</td>\n",
       "    </tr>\n",
       "    <tr>\n",
       "      <th>103160</th>\n",
       "      <td>12133</td>\n",
       "      <td>2024-12-30</td>\n",
       "      <td>0.373461</td>\n",
       "      <td>0.000000</td>\n",
       "      <td>12</td>\n",
       "      <td>82</td>\n",
       "      <td>29.937500</td>\n",
       "      <td>16.639186</td>\n",
       "      <td>1.037553</td>\n",
       "      <td>5.444872</td>\n",
       "      <td>2.8522</td>\n",
       "      <td>1.401803</td>\n",
       "    </tr>\n",
       "  </tbody>\n",
       "</table>\n",
       "<p>103161 rows × 12 columns</p>\n",
       "</div>"
      ],
      "text/plain": [
       "        GEOID        date  soil_moisture   rainfall  elev_min  elev_max  \\\n",
       "0       12001  2015-04-01       0.154073   0.225000        12        62   \n",
       "1       12001  2015-04-04       0.149908  40.025000        12        62   \n",
       "2       12001  2015-04-06       0.182036  46.364998        12        62   \n",
       "3       12001  2015-04-07       0.178972  13.530000        12        62   \n",
       "4       12001  2015-04-09       0.159802   0.180000        12        62   \n",
       "...       ...         ...            ...        ...       ...       ...   \n",
       "103156  12133  2024-12-19       0.279998   0.000000        12        82   \n",
       "103157  12133  2024-12-22       0.245652   0.000000        12        82   \n",
       "103158  12133  2024-12-25       0.222334  20.055000        12        82   \n",
       "103159  12133  2024-12-27       0.274217   0.000000        12        82   \n",
       "103160  12133  2024-12-30       0.373461   0.000000        12        82   \n",
       "\n",
       "        elev_mean   elev_std  slope_min  slope_max  slope_mean  slope_std  \n",
       "0       32.761905  12.895366   1.312327  16.027782      6.3840   4.614730  \n",
       "1       32.761905  12.895366   1.312327  16.027782      6.3840   4.614730  \n",
       "2       32.761905  12.895366   1.312327  16.027782      6.3840   4.614730  \n",
       "3       32.761905  12.895366   1.312327  16.027782      6.3840   4.614730  \n",
       "4       32.761905  12.895366   1.312327  16.027782      6.3840   4.614730  \n",
       "...           ...        ...        ...        ...         ...        ...  \n",
       "103156  29.937500  16.639186   1.037553   5.444872      2.8522   1.401803  \n",
       "103157  29.937500  16.639186   1.037553   5.444872      2.8522   1.401803  \n",
       "103158  29.937500  16.639186   1.037553   5.444872      2.8522   1.401803  \n",
       "103159  29.937500  16.639186   1.037553   5.444872      2.8522   1.401803  \n",
       "103160  29.937500  16.639186   1.037553   5.444872      2.8522   1.401803  \n",
       "\n",
       "[103161 rows x 12 columns]"
      ]
     },
     "execution_count": 374,
     "metadata": {},
     "output_type": "execute_result"
    }
   ],
   "source": [
    "soil_rain_elev"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 375,
   "id": "16a3dcd1-24e9-4a4c-b91d-9d65df7cb38f",
   "metadata": {},
   "outputs": [],
   "source": [
    "all_data = soil_rain_elev.merge(flood_events_df, how=\"left\", on=[\"GEOID\", \"date\"])"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 376,
   "id": "5c897fca-91bd-4ab2-a2c1-cd42b485bbe3",
   "metadata": {},
   "outputs": [],
   "source": [
    "all_data[\"flooded\"] = all_data[\"EVENT_TYPE\"].notna().astype(int)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 377,
   "id": "12ff3efc-12ef-470d-b9fa-d8b215708216",
   "metadata": {},
   "outputs": [
    {
     "data": {
      "text/plain": [
       "flooded\n",
       "0    102780\n",
       "1       624\n",
       "Name: count, dtype: int64"
      ]
     },
     "execution_count": 377,
     "metadata": {},
     "output_type": "execute_result"
    }
   ],
   "source": [
    "all_data['flooded'].value_counts()"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 378,
   "id": "1382e6c1-1925-4635-890f-47f3b9bbd969",
   "metadata": {},
   "outputs": [],
   "source": [
    "all_data = all_data.drop('EVENT_TYPE', axis=1)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 379,
   "id": "cfe95ef4-9404-4059-bf69-26cf12a2a3f3",
   "metadata": {},
   "outputs": [],
   "source": [
    "all_data.to_csv(\"florida_flood_dataset.csv\", index=False)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 380,
   "id": "05a3c220-f6e5-4907-abbb-680de0648a4c",
   "metadata": {},
   "outputs": [
    {
     "data": {
      "text/plain": [
       "Index(['GEOID', 'date', 'soil_moisture', 'rainfall', 'elev_min', 'elev_max',\n",
       "       'elev_mean', 'elev_std', 'slope_min', 'slope_max', 'slope_mean',\n",
       "       'slope_std', 'flooded'],\n",
       "      dtype='object')"
      ]
     },
     "execution_count": 380,
     "metadata": {},
     "output_type": "execute_result"
    }
   ],
   "source": [
    "all_data.columns"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3 (ipykernel)",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.12.7"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 5
}
