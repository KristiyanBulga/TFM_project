import boto3, json, datetime
from botocore.exceptions import ClientError

start_date = datetime.datetime(2024, 3, 7)
end_date = datetime.datetime(2024, 4, 23)
lambda_client = boto3.client('lambda', region_name='us-east-1')
for i in range(0, (end_date-start_date).days + 1):
    date = start_date + datetime.timedelta(days=i)
    custom_date = f"{date.year}_{date.month}_{date.day}_05_00_00"
    for place in ["g187486","g1435704"]:
        for plat in ["trip_advisor", "google_maps"]:
            print(custom_date, place, plat)
            function_name = 'data-process-dev-process-restaurant-data'
            function_params = {
                "trip_advisor_place_id": place, # ["g187486","g1435704"]
                "platform": plat, # ["trip_advisor", "google_maps"]
                "custom_date": custom_date
            }

            try:
                response = lambda_client.invoke(
                    FunctionName=function_name,
                    Payload=json.dumps(function_params),
                )
                print("Invoked function %s.", function_name)
                print("Response: ",response)
            except ClientError:
                print("Couldn't invoke function %s.", function_name)
                raise