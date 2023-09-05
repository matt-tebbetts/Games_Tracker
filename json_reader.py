import json

def ndjson_to_json(ndjson_file_path, output_file_path):
    # List to hold all the message objects
    data_list = []
    
    # Read the NDJSON file line by line and parse each line as a JSON object
    with open(ndjson_file_path, 'r') as file:
        for line in file:
            data_list.append(json.loads(line))
    
    # Write the list of message objects to the output file as a formatted JSON array
    with open(output_file_path, 'w') as file:
        json.dump(data_list, file, indent=4)

# Example usage
ndjson_file_path = "files/1096943693463814167/messages.json"
output_file_path = "files/1096943693463814167/messages_formatted.json"
ndjson_to_json(ndjson_file_path, output_file_path)