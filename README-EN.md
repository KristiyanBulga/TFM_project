# RestaurantScan Backend

[![en](https://img.shields.io/badge/lang-en-red.svg)](https://github.com/KristiyanBulga/TFM_project/blob/main/README-EN.md)
[![es](https://img.shields.io/badge/lang-es-yellow.svg)](https://github.com/KristiyanBulga/TFM_project/blob/main/README.md)

Master's degree final project about the development of a tool to evaluate a retailer’s online presence against its 
competitors. The aim of this project is to create a process of data extraction and homogenisation that can be applied to
any type of business. The development of this project has focused on restaurants.

## *TFM_project* Repository structure.
This repository contains the code responsible for creating the infrastructure in the AWS cloud. All deployment of the 
services have been deployed using **Serverless**. The structure of this repository is shown below.

### trip_advisor

In this folder you will find everything you need to automate the process of obtaining data through **web scraping** from
the Trip Advisor website. In the functions folder, you will find three files that correspond to the three functions 
deployed in AWS Lambda.
* **get_restaurants.py**: Retrieves the catalogue of restaurants in the specified province.
* **restaurant_scheduler.py**: Queue all requests for restaurant information in an SQS queue, which will call the 
following function.
* **get_restaurant_data.py**: Retrieves information for the specified restaurant.

The utils folder contains functions that are shared between the three functions. As discussed above, there is a 
serverless file with the resources and components to be deployed. In this case, there is a Docker file, this is because 
since **Selenium** package is required for web scraping, you need to have the necessary dependencies in Lambda for web 
scraping. To achieve this, we encapsulate the functions with all dependencies in a Docker image and the functions 
to create the Lambdas from this image.

### google_maps

Here we have what all we need to get the data provided by the Google Maps API. In addition to the normal 
serverless file, there is another serverless file that needs to be deployed before the other one. This file generates
layer with the dependencies that the functions need to work correctly. In this case, they are not deployed
with a Docker image as there are few dependencies required. The functions are:
* **get_google_maps_id.py**: This function is responsible for verifying that the restaurant we found using Trip Advisor 
is an existing restaurant. If we do not get any data by calling the Google Maps API, it means that the restaurant is not
valid.
* **schedule_restaurant.py**: Queue all requests for restaurant information into an SQS queue which will call the 
following function.
* **get_google_maps_data.py**: Retrieves, via the API, the Google Maps data about the restaurant that has been 
validated.

### data_processing

This folder can be divided into two sections that correspond to the two existing serverless. The first section is
for the data processing of the raw data from both platforms. In this case the serverless.yml file is used and also 
the Dockerfile as many dependencies are needed to execute the functions. The function of this section is:
* **process_data.py**: Processes and homogenises the data from both platforms in the same format so that they
can be compared.

The other part focuses on creating an API and preparing the data for this API. The functions are:
* **update_weekly_data.py** and **create_weekly_query.py**: The first one is responsible for updating the latest data for 
each restaurant in a table. The second is responsible for retrieving the data from this table and creating a file 
containing the result of the most used API request to speed up the data retrieval process for the API.
* **api.pi**: This function is responsible for detecting which API endpoint the request was made to, and is responsible 
for calling the function that returns the required information. These functions are defined in the files that begin with 
"*api_*".
* **add_notifications**: Gathers the processed data from the restaurants and checks the conditions for the notification. 
If the condition is met, the notification is created for the user.
