# RestaurantScan Backend

[![en](https://img.shields.io/badge/lang-en-red.svg)](https://github.com/KristiyanBulga/TFM_project/blob/main/README-EN.md)
[![es](https://img.shields.io/badge/lang-es-yellow.svg)](https://github.com/KristiyanBulga/TFM_project/blob/main/README.md)

Proyecto final de máster sobre el desarrollo de una herramienta para evaluar la presencia en la red de un comercio 
frente a sus competidores. El objetivo de este proyecto es crear un proceso de extracción y homogeneización de datos
que pueda ser llevado a cualquier tipo de negocios. El desarrollo de este proyecto se ha centrado en los restaurantes.

## Estructura del repositorio *TFM_project*

Este repositorio contiene el código encargado de generar la infraestructura en la nube de AWS. Todo el despliegue de 
servicios se ha realizado mediante **Serverless**. A continuación se detalla la estructura de este repositorio.

### trip_advisor

En esta carpeta se encuentra todo lo necesario para automatizar el proceso de obtención de datos a traves de **web 
scraping** de la página de Trip Advisor. En la carpeta de funciones se encuentran tres ficheros que corresponden con las
tres funciones que se despliegan en AWS Lambda.
* **get_restaurants.py**: Obtiene el catálogo de restaurantes de la provincia especificada
* **restaurant_scheduler.py**: Encola todas las peticiones de ontención de información de restaurante en una cola de SQS 
que activa la siguiente función.
* **get_restaurant_data.py**: Obtiene información del restaurante especificado.

La carpeta utils contiene funciones que se comparten entre las tres funciones. Como se ha comentado anteriormente,
hay un fichero serverless con los recursos y componentes que se van a desplegar. En este caso hay un fichero Docker,
esto es debido a que, como es necesario **Selenium** para la realizar el web scraping, se encesita tener las 
dependencias necesarias en Lambda, para ello encapsulamos las funciones con todas las dependencias en una imagen de 
Docker y se crean las Lambdas a partir de esta imagen.

### google_maps

En esta tenemos lo necesario para obtener los datos proporcionados por la API de Google Maps. Además del fichero 
serverless normal, existe un otro fichero serverless que debe ser desplegado antes que el otro. Este fichero genera
una capa con las dependencias que necesitan las funciones para funcionar correctamente. En este caso no se despliegan
con una imagen Docker ya que son pocas las dependencias necesarias. Las funciones son:
* **get_google_maps_id.py**: Esta función se encarga de validar que el restaurante que hemos descubierto con Trip 
Advisor es un restaurante que existe. Si llamando a la API de Google Maps no obtenemos datos, implica que el restaurante
no es válido.
* **schedule_restaurant.py**: Encola todas las peticiones de ontención de información de restaurante en una cola de SQS 
que activa la siguiente función.
* **get_google_maps_data.py**: Obtiene, a través de la API, los datos de Google Maps sobre el restaurante que ha sido 
validado.

### data_processing

Esta carpeta se puede dividir en dos secciones que coinciden con los dos serverless que existen. La primera sección es
la del procesamiento de los datos en bruto de ambas plataformas. En este caso se usa el fichero serverless.yml y también
el Dockerfile ya que se necesitan muchas dependencias para la ejecución de las funciones. La función de esta sección
es:
* **process_data.py**: Procesa y homogeneiza los datos de ambas plataformas en un mismo formato para que puedan ser
comparados.

La otra parte se centra en la creación de una API y en la preparación de los datos para esta API. Las funciones son:
* **update_weekly_data.py** y **create_weekly_query.py**: La primera se encarga de actualizar los datos más recientes de 
cada restaurante en una tabla. La segunda se encarga de recoger los datos de esta tabla y crear un fichero con la 
el resultado de la petición de la API más usada, de esta manera se agiliza el proceso de obtención de los datos.
* **api.pi**: Esta función se encarga de detectar a que endpoint de la API se ha realizado la petición y se encarga de 
llamar a la función que devuelva la información requerida. Estas funciones están definidas en los ficheros que empiezan 
por "*api_*".
* **add_notifications**: Recoge los datos procesados de los restaurantes y comprueba las condiciones de las 
configuraciones de notificaciones, y si se cumple la condición se crea la notificación para el usaurio.

