from json import JSONDecodeError

from flask import Flask, render_template
from flask_restful import Resource, Api, reqparse, fields, marshal_with
import http.client, urllib.request, urllib.parse, urllib.error, base64
import json
import requests

# Entiteiten == Provincie

parser = reqparse.RequestParser()

bingkey = "AsnS9px7kMQZMzI9y6Fpx9ZcuBdL5ula2wEpTOG4YDULxEGVj5rqGXEpCHuIxTl9"

app = Flask(__name__)
api = Api(app)
headers = {
    # Request headers
    'Ocp-Apim-Subscription-Key': 'a80d6af91407478c91c8288afd85452f',
}

osm_app_id = 'lLhrUyfFEtsQcqQygfnX'
osm_api_key = 'XpBpGZrvaawH8C_H6N0KEQ'

params = urllib.parse.urlencode({
    # Request parameters
    'datum': '{string}',
})

@app.route('/hello/')
@app.route('/hello/<name>')
def hello(name=None):
    return render_template('hello.html', name=name)

@app.route('/provincies/')
def provincies():
    conn = http.client.HTTPSConnection('delijn.azure-api.net')
    conn.request("GET", "/DLKernOpenData/v1/beta/entiteiten?%s" % params, "{body}", headers)
    response = conn.getresponse()
    data = response.read()
    # print(data)
    conn.close()
    provincies = {}
    data = json.loads(data)
    for i in range(len(data['entiteiten'])):
        name = data['entiteiten'][i - 1]['omschrijving']
        prov_id = data['entiteiten'][i]['entiteitnummer']
        # print("Provincie {0} heeft ID {1}".format(name, prov_id))
        provincies[prov_id] = name
    return render_template('provincies.html',entiteiten=data)


@app.route('/<provincie>/lijnen/')
def lijnen(provincie):
    conn = http.client.HTTPSConnection('delijn.azure-api.net')
    conn.request("GET", "/DLKernOpenData/v1/beta/entiteiten/{0}/lijnen".format(provincie), "{body}", headers)
    response = conn.getresponse()
    data = response.read()
    # print(data)
    conn.close()
    lijnen = json.loads(data)
    lijnen_mod = {}
    for i in range(len(lijnen['lijnen'])):
        lijnnummer = lijnen['lijnen'][i]['lijnnummer']
        traject = lijnen['lijnen'][i]['omschrijving']
        # print("Lijn {0} met traject {1}".format(lijnnummer, traject))
        if lijnen['lijnen'][i]['publiek'] == True:
            print(lijnen['lijnen'][i]['publiek'])
            lijnen_mod[lijnnummer] = traject
    return render_template('lijnenperprov.html', lijnen=lijnen)

@app.route('/<provincie>/lijnen/<lijnnr>/')
def lijnRegeling(provincie, lijnnr):
    conn = http.client.HTTPSConnection('delijn.azure-api.net')
    conn.request("GET", "/DLKernOpenData/v1/beta/lijnen/{0}/{1}".format(provincie, lijnnr), "{body}", headers)
    response = conn.getresponse()
    data = response.read()
    conn.close()
    return render_template('directionselect.html', data=json.loads(data))

@app.route('/<provincie>/lijnen/<lijnnr>/to/')
def lijnRegelingHeen(provincie, lijnnr):
    conn = http.client.HTTPSConnection('delijn.azure-api.net')
    conn.request("GET",
                 "/DLKernOpenData/v1/beta/lijnen/{0}/{1}/lijnrichtingen/HEEN/real-time".format(provincie, lijnnr),
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
            conn = http.client.HTTPSConnection('delijn.azure-api.net')
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
            if name not in haltes:
                haltes[name] = {}
                haltes[name]["time"] = []
            haltes[name]["time"].append(tijdstip)

            # Weer verwerken
            response = requests.get('https://api.openweathermap.org/data/2.5/weather?lat={0}&lon={1}&units=metric&appid=034c68ce1f92c2e0641421854a0f287d'.format(lati, longi))
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
                for i in range(len(route["response"]["route"][0]["leg"][0]["maneuver"])-1):
                    # for j in range(len(route["response"]["route"][0]["leg"][0]["maneuver"][i])-1):
                    # print(route["response"]["route"][0]["leg"][0]["maneuver"][i])
                    # print('\n')
                    rout_lat = route["response"]["route"][0]["leg"][0]["maneuver"][i]["position"]["latitude"]
                    rout_lon = route["response"]["route"][0]["leg"][0]["maneuver"][i]["position"]["longitude"]
                    rout_lat2 = route["response"]["route"][0]["leg"][0]["maneuver"][i+1]["position"]["latitude"]
                    rout_lon2 = route["response"]["route"][0]["leg"][0]["maneuver"][i+1]["position"]["longitude"]
                    route_coords.append([[rout_lat, rout_lon], [rout_lat2, rout_lon2]])
                        # print(rout_lat, rout_lon)

            haltes[name]["weather"] = w_desc
            haltes[name]["temp"] = temp
            haltes[name]["lati"] = lati
            haltes[name]["longi"] = longi
            prev_stop = name
    return render_template('onMap.html', haltes=haltes, routes=route_coords)

@app.route('/<provincie>/lijnen/<lijnnr>/from/')
def lijnRegelingTerug(provincie, lijnnr):
    conn = http.client.HTTPSConnection('delijn.azure-api.net')
    conn.request("GET", "/DLKernOpenData/v1/beta/lijnen/{0}/{1}/lijnrichtingen/TERUG/real-time".format(provincie, lijnnr),
                 "{body}", headers)
    response = conn.getresponse()
    data = response.read()
    conn.close()
    data=json.loads(data)
    haltes = {}
    for i in range(len(data["ritDoorkomsten"])-1):
        rit = data["ritDoorkomsten"][i]
        # Doorkomsten verwerken
        for j in range(len(rit["doorkomsten"])-1):
            halte = rit["doorkomsten"][j]["haltenummer"]
            # Locaties verwerken, nieuwe query
            conn = http.client.HTTPSConnection('delijn.azure-api.net')
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
            if name not in haltes:
                haltes[name] = {}
                haltes[name]["time"] = []
            haltes[name]["time"].append(tijdstip)
            response = requests.get(
                'https://api.openweathermap.org/data/2.5/weather?lat={0}&lon={1}&units=metric&appid=034c68ce1f92c2e0641421854a0f287d'.format(
                    lati, longi))
            weather = response.json()
            w_desc =  weather["weather"][0]["description"]
            temp = weather["main"]["temp"]
            haltes[name]["weather"] = w_desc
            haltes[name]["temp"] = temp
            haltes[name]["lati"] = lati
            haltes[name]["longi"] = longi
    return render_template('onMap.html', haltes=haltes)

class Welcome(Resource):
    def get(self):
        links = {}
        links['Provincies'] = '/provincies'
        links['Specifieke provincie'] = '/provincies/<provincie_id>'
        links['Alle lijnen'] = '/lijn'
        links['Lijnen per provincie'] = '/lijn/<provincie>'
        links['Specifieke lijn'] = '/lijn/<provincie>/<lijn_nummer>'
        links['Timetable'] = '/timetable/<provincie>/<lijnnummer>/<richting>'
        links['Realtime info'] = '/realtime/<provincie>/<lijnnummer>/<richting>'
        return links



class Lines(Resource):
    def get(self):
        try:
            conn = http.client.HTTPSConnection('delijn.azure-api.net')
            conn.request("GET", "/DLKernOpenData/v1/beta/lijnen?%s" % params, "{body}", headers)
            response = conn.getresponse()
            data = response.read()
            # print(data)
            conn.close()
            return json.loads(data)
        except Exception as e:
            print("[Errno {0}] {1}".format(e.errno, e.strerror))


class Line(Resource):
    def get(self, provincie, lijn):
        try:
            conn = http.client.HTTPSConnection('delijn.azure-api.net')
            conn.request("GET", "/DLKernOpenData/v1/beta/lijnen/{0}/{1}".format(provincie, lijn), "{body}", headers)
            response = conn.getresponse()
            data = response.read()
            # print(data)
            conn.close()
            return json.loads(data)
        except Exception as e:
            print("[Errno {0}] {1}".format(e.errno, e.strerror))


class Timetable(Resource):
    def get(self, provincie, lijnnummer, richting):
        try:
            conn = http.client.HTTPSConnection('delijn.azure-api.net')
            conn.request("GET",
                         "/DLKernOpenData/v1/beta/lijnen/{0}/{1}/lijnrichtingen/{2}/dienstregelingen".format(provincie, lijnnummer, richting.upper()),
                         "{body}", headers)
            response = conn.getresponse()
            data = response.read()
            conn.close()
            return json.loads(data)
        except JSONDecodeError as je:
            print(je)
        except Exception as e:
            print("[Errno {0}] {1}".format(e.errno, e.strerror))


class Realtimeinfo(Resource):
    def get(self, provincie, lijnnummer, richting):
        try:
            conn = http.client.HTTPSConnection('delijn.azure-api.net')
            conn.request("GET",
                         "/DLKernOpenData/v1/beta/lijnen/{0}/{1}/lijnrichtingen/{2}/real-time".format(provincie, lijnnummer, richting.upper()),
                         "{body}", headers)
            response = conn.getresponse()
            data = response.read()
            conn.close()
            return json.loads(data)
        except JSONDecodeError as je:
            print(je)
        except Exception as e:
            print("[Errno {0}] {1}".format(e.errno, e.strerror))


class Map(Resource):
    def get(self, lat, long):
        try:
            print("http://dev.virtualearth.net/REST/v1/Locations/{0},{1}?o=json&key={2}".format(lat, long, bingkey))
            conn = http.client.HTTPSConnection('http://dev.virtualearth.net')
            conn.request("GET",
                         "/REST/v1/Locations/{0},{1}?o=json&key={2}".format(lat, long, bingkey),
                         "{body}", headers)
            response = conn.getresponse()
            data = response.read()
            print(data)
            conn.close()
            return json.loads(data)
        except JSONDecodeError as je:
            print(je)
        except Exception as e:
            print("[Errno {0}] {1}".format(e.errno, e.strerror))


api.add_resource(Welcome,               '/')
api.add_resource(Lines,                 '/lijn')
api.add_resource(Line,                  '/lijn/<provincie>/<lijn>')
api.add_resource(Timetable,             '/timetable/<provincie>/<lijnnummer>/<richting>')
api.add_resource(Realtimeinfo,          '/realtime/<provincie>/<lijnnummer>/<richting>')
api.add_resource(Map,                   '/map/<lat>,<long>')


if __name__ == '__main__':
    app.run(debug=True)
