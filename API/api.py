from flask import jsonify, send_file
from . import api
import datetime
import requests
import urllib, urllib3

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


@api.route('/provinces/<prov>/lines/<line>/static/img/<name>')
def get_icon(prov, line, name):
    return send_file('static/img/'+name, mimetype='image/gif')


@api.route('/provinces/<prov>/static/img/<name>')
def get_logo(prov, name):
    return send_file('static/img/'+name, mimetype='image/gif')


@api.route('/get_timetable/<provincie>/<lijnnr>/to/')
def timetable_to(provincie, lijnnr):
    try:
        print(datetime.datetime.now())
        response = requests.get(
            base_url + "/DLKernOpenData/api/v1/lijnen/{0}/{1}/lijnrichtingen/HEEN/real-time".format(provincie, lijnnr),
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
        for i in range(min(5, len(data["ritDoorkomsten"]) - 1)):
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
            route_params += "waypoint" + str(0) + "=stopOver!" + str(stop_coords['0'][0]) + "," + str(
                stop_coords['0'][1]) + "&"
            for i in range(1, count - 1):
                route_params += "waypoint" + str(i) + "=passThrough!" + str(stop_coords[str(i)][0]) + "," + \
                                str(stop_coords[str(i)][1]) + "&"
            route_params += "waypoint" + str(count - 1) + "=geo!" + str(stop_coords[str(count - 1)][0]) + "," + \
                            str(stop_coords[str(count - 1)][1])
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


@api.route('/get_timetable/<provincie>/<lijnnr>/from/')
def timetable_from(provincie, lijnnr):
    try:
        print(datetime.datetime.now())
        response = requests.get(
            base_url + "/DLKernOpenData/api/v1/lijnen/{0}/{1}/lijnrichtingen/TERUG/real-time".format(provincie, lijnnr),
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
        for i in range(min(5, len(data["ritDoorkomsten"]) - 1)):
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
            route_params += "waypoint" + str(0) + "=stopOver!" + str(stop_coords['0'][0]) + "," + str(
                stop_coords['0'][1]) + "&"
            for i in range(1, count - 1):
                route_params += "waypoint" + str(i) + "=passThrough!" + str(stop_coords[str(i)][0]) + "," + \
                                str(stop_coords[str(i)][1]) + "&"
            route_params += "waypoint" + str(count - 1) + "=geo!" + str(stop_coords[str(count - 1)][0]) + "," + \
                            str(stop_coords[str(count - 1)][1])
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
