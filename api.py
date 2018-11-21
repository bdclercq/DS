import datetime
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

@app.route('/')
@app.route('/provincies/')
def provincies():
    conn = http.client.HTTPSConnection('delijn.azure-api.net')
    conn.request("GET", "/DLKernOpenData/v1/beta/entiteiten?%s" % params, "{body}", headers)
    response = conn.getresponse()
    data = response.read()
    conn.close()
    provincies = {}
    data = json.loads(data)
    for i in range(len(data['entiteiten'])):
        name = data['entiteiten'][i - 1]['omschrijving']
        prov_id = data['entiteiten'][i]['entiteitnummer']
        provincies[prov_id] = name
    return render_template('provincies.html',entiteiten=data)


@app.route('/<provincie>/lijnen/')
def lijnen(provincie):
    conn = http.client.HTTPSConnection('delijn.azure-api.net')
    conn.request("GET", "/DLKernOpenData/v1/beta/entiteiten/{0}/lijnen".format(provincie), "{body}", headers)
    response = conn.getresponse()
    data = response.read()
    conn.close()
    lijnen = json.loads(data)
    lijnen_mod = {}
    for i in range(len(lijnen['lijnen'])):
        lijnnummer = lijnen['lijnen'][i]['lijnnummer']
        traject = lijnen['lijnen'][i]['omschrijving']
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
            dt = datetime.datetime.fromisoformat(tijdstip)
            # print(dt)
            if name not in haltes:
                haltes[name] = {}
                haltes[name]["time"] = []
            haltes[name]["time"].append(dt.time().isoformat())

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
                    rout_lat = route["response"]["route"][0]["leg"][0]["maneuver"][i]["position"]["latitude"]
                    rout_lon = route["response"]["route"][0]["leg"][0]["maneuver"][i]["position"]["longitude"]
                    rout_lat2 = route["response"]["route"][0]["leg"][0]["maneuver"][i+1]["position"]["latitude"]
                    rout_lon2 = route["response"]["route"][0]["leg"][0]["maneuver"][i+1]["position"]["longitude"]
                    route_coords.append([[rout_lat, rout_lon], [rout_lat2, rout_lon2]])

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
            dt = datetime.datetime.fromisoformat(tijdstip)
            if name not in haltes:
                haltes[name] = {}
                haltes[name]["time"] = []
            haltes[name]["time"].append(dt.time().isoformat())
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


if __name__ == '__main__':
    app.run(debug=True)
