import json
import simplejson
import socketserver
import http.server
from urllib.parse import urlparse, parse_qs
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from mongo_auth import mongo_collection
#mongo_auth contine credentialele pentru DB-ul de mongo -> mongo_collection = MongoClient(MONGO_URI)[MONGO_DB][MONGO_COLLECTION]
PORT = 8000
LOCALHOST = "127.0.0.1"

class MyHandler(http.server.SimpleHTTPRequestHandler):

    def do_GET(self):
        parsedURL = urlparse(self.path)
        (resource_name, resource_id) = self.get_path_infos(parsedURL.path)
        match resource_name:
            case 'bikes':
                if resource_id:
                    self.get_bike_by_id(bike_id = resource_id)
                else:
                    self.get_all_bikes()
            case _:
                self.bad_request('Invalid route')
        return
    
    def do_POST(self):
        parsedURL = urlparse(self.path)
        (resource_name, resource_id) = self.get_path_infos(parsedURL.path)
        match resource_name:
            case 'bikes':
                content_len = int(self.headers.get('Content-Length'))
                post_body = self.rfile.read(content_len)
                self.add_bike(json.loads(post_body))
            case _:
                self.bad_request('Invalid route')
        return
    
    def do_DELETE(self):
        parsedURL = urlparse(self.path)
        (resource_name, resource_id) = self.get_path_infos(parsedURL.path)
        match resource_name:
            case 'bikes':
                if resource_id:
                    self.delete_bike_by_id(bike_id = resource_id)
                    return
                else:
                    self.bad_request('no ID')
                    return
            case _:
                self.bad_request('Invalid route')
                return
        return
    
    def do_PUT(self):
        parsedURL = urlparse(self.path)
        (resource_name, resource_id) = self.get_path_infos(parsedURL.path)
        match resource_name:
            case 'bikes':
                if resource_id:
                    content_len = int(self.headers.get('Content-Length'))
                    post_body = self.rfile.read(content_len)
                    new_data= json.loads(post_body)
                    self.update_bike_by_id(resource_id, new_data)
                else:
                    self.bad_request('no ID')
            case _:
                self.bad_request('Invalid route')
        return

    def get_all_bikes(self):
        response = {}          
        results = mongo_collection.find({})
        for result in results:
            response[result["_id"]] = {"type":result["type"]}
        self.request_ok(response_text=json.dumps(response))
        return
    
    def get_bike_by_id(self, bike_id):
        result = mongo_collection.find_one({"_id":bike_id})
        if result:
            response = json.dumps(result)            
            self.request_ok(response)
        else:
            self.resource_not_found(f'ID not found: {bike_id}')
        return

    def add_bike(self, new_bike_data):
        if "type" in new_bike_data and "_id" in new_bike_data:
            new_bike_data["_id"] = str(new_bike_data["_id"])
            if self.id_in_collection(new_bike_data["_id"]):
                self.resource_conflict()
                return
            mongo_collection.insert_one(new_bike_data)
            self.resource_created()
            return
        else:
            self.bad_request("Invalid Format")
            return

    def delete_bike_by_id(self, bike_id):
        if self.id_in_collection(bike_id):
            mongo_collection.delete_one({"_id":bike_id})            
            self.request_ok()
        else:
            self.resource_not_found()
        return

    def update_bike_by_id(self, bike_id, new_data):
        if not "type" in new_data:
            self.bad_request('Invalid Data')
            return
        if self.id_in_collection(bike_id):
            filter = {"_id":bike_id}
            new_values = { "$set": { "type":new_data["type"]}}
            mongo_collection.update_one(filter, new_values)
            self.request_ok()
        else:
            data = {"_id":bike_id, "type":new_data["type"]}
            self.add_bike(data)
        return

    def get_path_infos(self, path):
        resource_name = None
        resource_id = None
        
        path_infos = path.split('/')
        if len(path_infos) == 2:
            resource_name = path_infos[1]
            resource_id = None
        if len(path_infos) == 3:
            resource_name = path_infos[1]
            resource_id = path_infos[2]
        
        return (resource_name, resource_id)
    
    def bad_request(self, response_text = None):
        self.respond(400, response_text)
        return

    def resource_not_found(self, response_text = None):
        self.respond(404, response_text)
        return
        
    def resource_created(self, response_text = None):
        self.respond(201, response_text)
        return

    def request_ok(self, response_text = None):
        self.respond(200, response_text)
        return

    def resource_conflict(self, response_text = None):
        self.respond(409, response_text)
        return

    def respond(self, status_code, response_text = None):
        self.send_response(status_code)
        self.end_headers()
        if response_text:
            self.wfile.write(response_text.encode())
        return
   
    def id_in_collection(self, bike_id):
        filter = {"_id":bike_id}
        if mongo_collection.find_one(filter):
            return True
        return False


Handler = MyHandler

try:
    with socketserver.TCPServer((LOCALHOST, PORT), Handler) as httpd:
        print(f"{LOCALHOST}:{PORT}")
        httpd.serve_forever()

except KeyboardInterrupt:
    print("Stopping by Ctrl+C")
    httpd.server_close()
