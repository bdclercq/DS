from flask import jsonify
from . import api
import datetime
import http.client
import json
import requests
import urllib, urllib3
import sys

# Entiteiten == Provincie

base_url = 'https://api.delijn.be'

headers = {
    # Request headers
    'Ocp-Apim-Subscription-Key': 'a80d6af91407478c91c8288afd85452f',
}

osm_app_id = 'lLhrUyfFEtsQcqQygfnX'
osm_api_key = 'XpBpGZrvaawH8C_H6N0KEQ'

params = urllib.parse.urlencode({})


@api.route('/get_provinces/')
def get_provinces():
    try:
        try:
            response = requests.get(base_url + "/DLKernOpenData/api/v1/entiteiten", headers=headers)
            data = response.json()
            response_object = {
                'status': 'success',
                'data': {
                    'provinces': [prov for prov in data["entiteiten"]]
                }
            }
            return jsonify(response_object), 200
        except:
            response_object = {
                'status': 'fail',
                'data': {
                    'message': 'Request failed'
                }
            }
            return jsonify(response_object), 404
    except:
        response_object = {
            'status': 'fail',
            'data': {
                'message': 'Please try again later (failure in getting provinces).'
            }
        }
        return jsonify(response_object), 404


@api.route('/get_lines/<provincie>')
def lijnen(provincie):
    try:
        response = requests.get(base_url + "/DLKernOpenData/v1/beta/entiteiten/{0}/lijnen".format(provincie),
                                headers=headers)
        data = response.json()
        response_object = {
            'status': 'success',
            'data': {
                'lines': [line for line in data['lijnen']]
            }
        }
        return jsonify(response_object), 200
    except:
        response_object = {
            'status': 'fail',
            'data': {
                'message': 'Something went wrong.'
            }
        }
        return jsonify(response_object), 400


@api.route('/get_timetable/<provincie>/<lijnnr>/to/')
def timetable_to(provincie, lijnnr):

    try:
        print(datetime.datetime.now())
        response = requests.get(base_url + "/DLKernOpenData/api/v1/lijnen/{0}/{1}/lijnrichtingen/HEEN/real-time".format(provincie, lijnnr),
                                headers=headers)
        data = response.json()
        try:
            if data['statusCode'] == 404:
                response_object = {
                    'status': 'fail',
                    'message': data['message']
                }
                return jsonify(response_object), 404
        except:
            pass  # No error code thrown
        stops = {}
        line_route = 0
        stop_coords = {}
        count = 0
        for i in range(min(2, len(data["ritDoorkomsten"]) - 1)):
            rit = data["ritDoorkomsten"][i]
            # Doorkomsten verwerken
            for j in range(len(rit["doorkomsten"]) - 1):
                halte = rit["doorkomsten"][j]["haltenummer"]
                # Locaties verwerken, nieuwe query
                response = requests.get(
                    base_url + "/DLKernOpenData/v1/beta/haltes/{0}/{1}?".format(provincie, halte), headers=headers)
                halteData = response.json()

                try:
                    if halteData['code'] == '404':
                        response_object = {
                            'status': 'fail',
                            'message': halteData['boodschap']
                        }
                        return jsonify(response_object), 404
                except:
                    pass  # No error code thrown

                try:
                    lati = halteData["geoCoordinaat"]["latitude"]
                    longi = halteData["geoCoordinaat"]["longitude"]

                    name = halteData["omschrijving"]

                    tijdstip = rit["doorkomsten"][j]["dienstregelingTijdstip"]
                    dt = datetime.datetime.fromisoformat(tijdstip)
                    # print(dt)
                    if name not in stops:
                        stops[name] = {
                            'time': [],
                            'name': name,
                            'route': '',
                            'weather': '',
                            'temp': '',
                            'lati': '',
                            'longi': ''
                        }
                        stop_coords[str(count)] = [lati, longi]
                        count += 1
                    stops[name]["time"].append(dt.time().isoformat())

                    # Weer verwerken
                    response = requests.get(
                        'https://api.openweathermap.org/data/2.5/weather?lat={0}&lon={1}&units=metric&appid=034c68ce1f92c2e0641421854a0f287d'.format(
                            lati, longi))
                    weather = response.json()
                    w_desc = weather["weather"][0]["description"]
                    temp = weather["main"]["temp"]

                    stops[name]["weather"] = w_desc
                    stops[name]["temp"] = temp
                    stops[name]["lati"] = lati
                    stops[name]["longi"] = longi
                except:
                    if halteData['statusCode'] == 404:
                        response_object = {
                            'status': 'fail',
                            'message': halteData['message']
                        }
                        return jsonify(response_object), 404
                    print("Data:", halteData)

        print(datetime.datetime.now())
        try:
            route_params = ""
            route_params += "waypoint" + str(0) + "=stopOver!" + str(stop_coords['0'][0]) + "," + str(stop_coords['0'][1]) + "&"
            for i in range(1, count-1):
                route_params += "waypoint"+str(i)+"=passThrough!"+str(stop_coords[str(i)][0])+"," + \
                                str(stop_coords[str(i)][1])+"&"
            route_params += "waypoint"+str(count-1)+"=geo!"+str(stop_coords[str(count-1)][0])+"," + \
                            str(stop_coords[str(count-1)][1])
            print('https://route.api.here.com/routing/7.2/calculateroute.json?{0}&mode=balanced;publicTransport;traffic:disabled&routeattributes=none,sh&app_id={1}&app_code={2}'.format(
                    route_params, osm_app_id, osm_api_key))
            response = requests.get(
                'https://route.api.here.com/routing/7.2/calculateroute.json?{0}&mode=balanced;publicTransport;traffic:disabled&routeattributes=none,sh&&app_id={1}&app_code={2}'.format(
                    route_params, osm_app_id, osm_api_key))
            line_route = response.json()['response']['route'][0]['shape']
            coords = [r.split(",") for r in line_route]
        except:
            response_object = {
                'status': 'fail',
                'message': 'Something went wrong getting the routes'
            }
            return jsonify(response_object), 404
        response_object = {
            'status': 'success',
            'data': {
                'stops': [stops[halte] for halte in stops],
                'routes': coords
            }
        }
        print(datetime.datetime.now())
        return jsonify(response_object), 200
    except urllib3.exceptions.ProtocolError as pe:
        response_object = {
            'status': 'fail',
            'message': str(pe)
        }
        return jsonify(response_object), 500


@api.route('/<provincie>/lijnen/<lijnnr>/from/')
def lijnRegelingTerug(provincie, lijnnr):
    response_object = {
        'status': 'fail',
        'data': {
            'message': 'Something went wrong.'
        }
    }
    try:
        conn = http.client.HTTPSConnection(base_url)
        conn.request("GET",
                     "/DLKernOpenData/v1/beta/lijnen/{0}/{1}/lijnrichtingen/TERUG/real-time".format(provincie, lijnnr),
                     "{body}", headers)
        response = conn.getresponse()
        data = response.read()
        conn.close()
        data = json.loads(data)
        haltes = {}
        route_coords = []
        for i in range(len(data["ritDoorkomsten"]) - 1):
            rit = data["ritDoorkomsten"][i]
            prev_stop = 0
            # Doorkomsten verwerken
            for j in range(len(rit["doorkomsten"]) - 1):
                halte = rit["doorkomsten"][j]["haltenummer"]
                # Locaties verwerken, nieuwe query
                conn = http.client.HTTPSConnection(base_url)
                conn.request("GET",
                             "/DLKernOpenData/v1/beta/haltes/{0}/{1}".format(provincie, halte),
                             "{body}", headers)
                response = conn.getresponse()
                halteData = response.read()
                conn.close()
                halteData = json.loads(halteData)
                lati = halteData["geoCoordinaat"]["latitude"]
                longi = halteData["geoCoordinaat"]["longitude"]
                name = halteData["omschrijving"]

                tijdstip = rit["doorkomsten"][j]["dienstregelingTijdstip"]
                dt = datetime.datetime.fromisoformat(tijdstip)
                # print(dt)
                if name not in haltes:
                    haltes[name] = {}
                    haltes[name]["time"] = []
                haltes[name]["time"].append(dt.time().isoformat())

                # Weer verwerken
                response = requests.get(
                    'https://api.openweathermap.org/data/2.5/weather?lat={0}&lon={1}&units=metric&appid=034c68ce1f92c2e0641421854a0f287d'.format(
                        lati, longi))
                weather = response.json()
                w_desc = weather["weather"][0]["description"]
                temp = weather["main"]["temp"]

                # Routes verwerken
                if prev_stop != 0:
                    lat1 = haltes[prev_stop]["lati"]
                    long1 = haltes[prev_stop]["longi"]
                    response = requests.get(
                        'https://route.api.here.com/routing/7.2/calculateroute.json?waypoint0=geo!{0},{1}&waypoint1=geo!{2},{3}&mode=balanced;publicTransport&app_id={4}&app_code={5}'.format(
                            lat1, long1, lati, longi, osm_app_id, osm_api_key))
                    route = response.json()
                    for i in range(len(route["response"]["route"][0]["leg"][0]["maneuver"]) - 1):
                        rout_lat = route["response"]["route"][0]["leg"][0]["maneuver"][i]["position"]["latitude"]
                        rout_lon = route["response"]["route"][0]["leg"][0]["maneuver"][i]["position"]["longitude"]
                        rout_lat2 = route["response"]["route"][0]["leg"][0]["maneuver"][i + 1]["position"]["latitude"]
                        rout_lon2 = route["response"]["route"][0]["leg"][0]["maneuver"][i + 1]["position"]["longitude"]
                        route_coords.append([[rout_lat, rout_lon], [rout_lat2, rout_lon2]])

                haltes[name]["weather"] = w_desc
                haltes[name]["temp"] = temp
                haltes[name]["lati"] = lati
                haltes[name]["longi"] = longi
                prev_stop = name
        response_object['status'] = 'success'
        response_object['data'] = haltes
        return jsonify(response_object, 200)
    except:
        return jsonify(response_object, 400)
